#!/usr/bin/env node
const { program } = require('commander');
const fs = require('fs');
const path = require('path');
const axios = require('axios');

const CONFIG_PATH = path.join(process.env.HOME, '.wiki.json');

function loadConfig() {
    let cfg = {
        WIKI_ROOT: path.join(process.env.HOME, 'Documents', 'kevinhusnotes', '_WIKI'),
        INBOX_DIR: path.join(process.env.HOME, 'Documents', 'kevinhusnotes', '00_Inbox'),
        RAW_ARCHIVE_DIR: path.join(process.env.HOME, 'Documents', 'kevinhusnotes', '30_Resources', 'Raw'),
        OPENAI_API_KEY: ''
    };
    if (fs.existsSync(CONFIG_PATH)) {
        Object.assign(cfg, JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8')));
    }
    // Environment variables override config file
    if (process.env.WIKI_ROOT) cfg.WIKI_ROOT = process.env.WIKI_ROOT;
    if (process.env.INBOX_DIR) cfg.INBOX_DIR = process.env.INBOX_DIR;
    if (process.env.RAW_ARCHIVE_DIR) cfg.RAW_ARCHIVE_DIR = process.env.RAW_ARCHIVE_DIR;
    if (process.env.OPENAI_API_KEY) cfg.OPENAI_API_KEY = process.env.OPENAI_API_KEY;
    return cfg;
}

const config = loadConfig();

const NODES_DIR = path.join(config.WIKI_ROOT, 'nodes');
const INDEX_FILE = path.join(config.WIKI_ROOT, 'index.md');
const LOG_FILE = path.join(config.WIKI_ROOT, 'log.md');

function initDirectories() {
    [config.WIKI_ROOT, config.INBOX_DIR, config.RAW_ARCHIVE_DIR, NODES_DIR].forEach(dir => {
        if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    });
    if (!fs.existsSync(INDEX_FILE)) fs.writeFileSync(INDEX_FILE, '# Wiki Catalog\n');
    if (!fs.existsSync(LOG_FILE)) fs.writeFileSync(LOG_FILE, '# Wiki Log\n');
}

async function extractConcepts(content) {
    if (!config.OPENAI_API_KEY) throw new Error("OPENAI_API_KEY is not set. Run 'wiki config --api-key <key>' or set the environment variable.");
    
    let currentIndex = "";
    if (fs.existsSync(INDEX_FILE)) currentIndex = fs.readFileSync(INDEX_FILE, 'utf8');

    const prompt = `You are a wiki librarian. Extract the single main concept from the provided raw text. 
Format your output as a strict JSON object with:
- "title": MUST match an existing node title if synthesizing into it, otherwise a new concise filename (no spaces/special chars)
- "description": a one-line summary
- "l1": The top-level category (e.g. Artificial Intelligence)
- "l2": The mid-level category (e.g. Agentic Systems)
- "l3": The granular category (e.g. Architecture & Memory)
- "content": A markdown section summarizing the core ideas. If synthesizing into an existing concept, update its summary. Formatted with '## Core Ideas' and '## Evolution / Contradictions'.
- "is_new": boolean (true if creating a new node, false if updating an existing node found in the index)
    
Use this current taxonomy context to route the file appropriately, or invent a new category if it doesn't fit:
${currentIndex.substring(0, 1500)}

Raw text:
${content}
`;

    const response = await axios.post('https://api.openai.com/v1/chat/completions', {
        model: "gpt-4o",
        response_format: { type: "json_object" },
        messages: [{ role: "system", content: prompt }]
    }, {
        headers: { 'Authorization': `Bearer ${config.OPENAI_API_KEY}` }
    });

    return JSON.parse(response.data.choices[0].message.content);
}

function updateIndex(data, filename) {
    let indexData = fs.readFileSync(INDEX_FILE, 'utf8');
    const entry = `- [[${filename}]] - ${data.description}`;
    
    const l1Header = `## ${data.l1}`;
    const l2Header = `### ${data.l2}`;
    const l3Header = `#### ${data.l3}`;
    
    let newIndex = [];
    let lines = indexData.split('\n');
    let inserted = false;
    let inL1 = false, inL2 = false, inL3 = false;

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        newIndex.push(line);
        
        if (line.startsWith('## ') && line === l1Header) inL1 = true;
        else if (line.startsWith('## ')) inL1 = false;
        
        if (inL1 && line === l2Header) inL2 = true;
        else if (line.startsWith('### ')) inL2 = false;

        if (inL2 && line === l3Header) {
            newIndex.push(entry);
            inserted = true;
        }
    }
    
    if (!inserted) {
        newIndex.push(`\n${l1Header}`);
        newIndex.push(`${l2Header}`);
        newIndex.push(`${l3Header}`);
        newIndex.push(entry);
    }
    
    fs.writeFileSync(INDEX_FILE, newIndex.join('\n'));
}

function isHiddenPath(targetPath) {
    return targetPath.split(path.sep).some(part => part.startsWith('.') && part.length > 1);
}

function collectMarkdownFiles(dirPath) {
    const entries = fs.readdirSync(dirPath, { withFileTypes: true });
    let files = [];

    for (const entry of entries) {
        if (entry.name.startsWith('.')) continue;

        const entryPath = path.join(dirPath, entry.name);
        if (entry.isDirectory()) {
            files = files.concat(collectMarkdownFiles(entryPath));
            continue;
        }

        if (entry.isFile() && entry.name.endsWith('.md') && !isHiddenPath(entryPath)) {
            files.push(entryPath);
        }
    }

    return files;
}

async function ingestFile(file, options = {}) {
    const keep = Boolean(options.keep);

    initDirectories();
    const rawPath = path.resolve(file);
    console.log(`Reading raw file: ${rawPath}`);
    const content = fs.readFileSync(rawPath, 'utf8');

    console.log('Extracting concepts and inferring taxonomy via LLM...');
    const data = await extractConcepts(content);
    console.log(`Inferred: ${data.l1} -> ${data.l2} -> ${data.l3}`);

    const dateStr = new Date().toISOString().split('T')[0];
    const baseFileName = path.basename(rawPath, '.md');

    
                const nodePath = path.join(NODES_DIR, `${data.title}.md`);
                let nodeContent = "";
                if (!data.is_new && fs.existsSync(nodePath)) {
                    console.log(`Synthesizing into existing node: ${data.title}`);
                    let existingContent = fs.readFileSync(nodePath, 'utf8');
                    // Simple append for sources, and replace body (in a real system, we'd use an LLM edit pass)
                    // For now, we will just let the LLM rewrite the whole body
                    nodeContent = `---
Created: '${dateStr}'
Updated: '${dateStr}'
Tags: ['#concept', '#llm-wiki']
---
# ${data.title}

${data.description}

${data.content}

## Sources
- [[${baseFileName}]]
`;
                    // naive append sources - we should preserve old sources
                    const oldSourcesMatch = existingContent.match(/## Sources[\s\S]*/);
                    if (oldSourcesMatch) {
                        const oldSources = oldSourcesMatch[0].replace('## Sources', '').trim();
                        if (!oldSources.includes(baseFileName)) {
                             nodeContent = nodeContent.replace('- [[' + baseFileName + ']]', oldSources + '\n- [[' + baseFileName + ']]');
                        } else {
                             nodeContent = nodeContent.replace('- [[' + baseFileName + ']]', oldSources);
                        }
                    }
                } else {
                    console.log(`Creating new node: ${data.title}`);
                    nodeContent = `---
Created: '${dateStr}'
Updated: '${dateStr}'
Tags: ['#concept', '#wiki']
---
# ${data.title}

${data.description}

${data.content}

## Sources
- [[${baseFileName}]]
`;

    const nodePath = path.join(NODES_DIR, `${data.title}.md`);
    fs.writeFileSync(nodePath, nodeContent);
    console.log(`Created node: ${nodePath}`);

    if (data.is_new) updateIndex(data, data.title);
    console.log('Updated index.md with new link.');

    const logEntry = `\n## [${dateStr}] Ingest | ${baseFileName} | Pages touched: [[${data.title}]]`;
    fs.appendFileSync(LOG_FILE, logEntry);

    if (keep) {
        console.log('Keeping original raw file in place (--keep enabled).');
    } else {
        const archivePath = path.join(config.RAW_ARCHIVE_DIR, path.basename(rawPath));
        fs.copyFileSync(rawPath, archivePath);
        fs.unlinkSync(rawPath);
        console.log(`Archived raw file to ${archivePath}`);
    }

    console.log('Ingest complete.');
}

program.command('config')
    .description('Generate or update the local configuration file (~/.wiki.json)')
    .option('--wiki-root <path>', 'Set WIKI_ROOT')
    .option('--inbox-dir <path>', 'Set INBOX_DIR')
    .option('--raw-archive-dir <path>', 'Set RAW_ARCHIVE_DIR')
    .option('--api-key <key>', 'Set OPENAI_API_KEY')
    .action((options) => {
        let cfg = {};
        if (fs.existsSync(CONFIG_PATH)) cfg = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
        
        if (options.wikiRoot) cfg.WIKI_ROOT = path.resolve(options.wikiRoot);
        if (options.inboxDir) cfg.INBOX_DIR = path.resolve(options.inboxDir);
        if (options.rawArchiveDir) cfg.RAW_ARCHIVE_DIR = path.resolve(options.rawArchiveDir);
        if (options.apiKey) cfg.OPENAI_API_KEY = options.apiKey;
        
        // Setup defaults if not existing
        if (!cfg.WIKI_ROOT) cfg.WIKI_ROOT = path.join(process.env.HOME, 'Documents', 'kevinhusnotes', '_WIKI');
        if (!cfg.INBOX_DIR) cfg.INBOX_DIR = path.join(process.env.HOME, 'Documents', 'kevinhusnotes', '00_Inbox');
        if (!cfg.RAW_ARCHIVE_DIR) cfg.RAW_ARCHIVE_DIR = path.join(process.env.HOME, 'Documents', 'kevinhusnotes', '30_Resources', 'Raw');
        
        fs.writeFileSync(CONFIG_PATH, JSON.stringify(cfg, null, 2));
        console.log(`Configuration saved to ${CONFIG_PATH}`);
    });

program.command('add <file>')
    .description('Ingest a raw file into the Wiki')
    .option('--keep', 'Keep the original raw file instead of archiving it')
    .action(async (file, options) => {
        try {
            await ingestFile(file, { keep: options.keep });
        } catch (e) {
            console.error('Error:', e.message);
        }
    });

program.command('batch <dir>')
    .description('Recursively ingest all markdown files in a directory while keeping originals')
    .action(async (dir) => {
        try {
            const rootDir = path.resolve(dir);
            const files = collectMarkdownFiles(rootDir);
            console.log(`Found ${files.length} markdown files in ${rootDir}`);

            for (let i = 0; i < files.length; i++) {
                console.log(`\n[${i + 1}/${files.length}] Ingesting ${files[i]}`);
                await ingestFile(files[i], { keep: true });
            }

            console.log(`Batch ingest complete. Processed ${files.length} files.`);
        } catch (e) {
            console.error('Error:', e.message);
        }
    });


function findMarkdownFiles(dir, fileList = []) {
    const files = fs.readdirSync(dir);
    for (const file of files) {
        if (file.startsWith('.')) continue; // skip hidden
        const filePath = path.join(dir, file);
        if (fs.statSync(filePath).isDirectory()) {
            findMarkdownFiles(filePath, fileList);
        } else if (file.endsWith('.md')) {
            fileList.push(filePath);
        }
    }
    return fileList;
}

program.command('batch <dir>')
    .description('Batch ingest all markdown files in a directory')
    .option('--keep', 'Do not move or delete the raw files', true)
    .action(async (dir, options) => {
        initDirectories();
        const fullDir = path.resolve(dir);
        console.log(`Scanning directory: ${fullDir}`);
        const files = findMarkdownFiles(fullDir);
        console.log(`Found ${files.length} markdown files. Beginning batch ingest...`);
        
        for (const file of files) {
            console.log(`\n--- Processing ${file} ---`);
            // we simulate the 'add' action logic here or we can just extract it to a function
            try {
                const content = fs.readFileSync(file, 'utf8');
                const data = await extractConcepts(content);
                const dateStr = new Date().toISOString().split('T')[0];
                const baseFileName = path.basename(file, '.md');
                
                const nodeContent = `---
Created: '${dateStr}'
Updated: '${dateStr}'
Tags: ['#concept', '#llm-wiki']
---
# ${data.title}

${data.description}

${data.content}

## Sources
- [[${baseFileName}]]
`;
                const nodePath = path.join(NODES_DIR, `${data.title}.md`);
                fs.writeFileSync(nodePath, nodeContent);
                console.log(`Created/Updated node: ${nodePath}`);
                updateIndex(data, data.title);
                
                const logEntry = `\n## [${dateStr}] Batch Ingest | ${baseFileName} | Pages touched: [[${data.title}]]`;
                fs.appendFileSync(LOG_FILE, logEntry);
                
                if (!options.keep) {
                    const archivePath = path.join(config.RAW_ARCHIVE_DIR, path.basename(file));
                    fs.copyFileSync(file, archivePath);
                    fs.unlinkSync(file);
                }
            } catch (e) {
                console.error(`Failed to process ${file}: ${e.message}`);
            }
        }
        console.log('\nBatch processing complete.');
    });

program.command('lint')
    .description('Check the wiki for orphan nodes and missing index links')
    .action(() => {
        initDirectories();
        console.log('Linting wiki...');
        const indexData = fs.readFileSync(INDEX_FILE, 'utf8');
        const nodes = fs.readdirSync(NODES_DIR).filter(f => f.endsWith('.md'));
        
        let orphans = [];
        nodes.forEach(node => {
            const title = path.basename(node, '.md');
            if (!indexData.includes(`[[${title}]]`)) {
                orphans.push(title);
            }
        });
        
        if (orphans.length > 0) {
            console.log('⚠️ Orphan Nodes Found (not in index.md):');
            orphans.forEach(o => console.log(`  - ${o}`));
        } else {
            console.log('✅ All nodes are properly indexed.');
        }
    });

program.command('search <query>')
    .description('Search the index.md catalog')
    .action((query) => {
        initDirectories();
        const indexData = fs.readFileSync(INDEX_FILE, 'utf8');
        const lines = indexData.split('\n');
        const results = lines.filter(l => l.toLowerCase().includes(query.toLowerCase()));
        
        if (results.length > 0) {
            console.log(`Found ${results.length} matches in index:`);
            results.forEach(r => console.log(r));
        } else {
            console.log('No matches found.');
        }
    });

program.parse(process.argv);
