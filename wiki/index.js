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
    if (!config.OPENAI_API_KEY) throw new Error("OPENAI_API_KEY is not set. Run 'wiki config --api-key <key>'");
    let currentIndex = fs.existsSync(INDEX_FILE) ? fs.readFileSync(INDEX_FILE, 'utf8') : "";

    const prompt = `You are a wiki librarian. Extract the main concept from the provided raw text. 
Format your output as a strict JSON object with:
- "title": MUST match an existing node title if synthesizing into it, otherwise a new concise filename (no spaces/special chars)
- "description": a one-line summary
- "l1": The top-level category (e.g. Artificial Intelligence)
- "l2": The mid-level category (e.g. Agentic Systems)
- "l3": The granular category (e.g. Architecture & Memory)
- "content": A markdown section summarizing the core ideas. If synthesizing into an existing concept, update its summary to include new info. Formatted with '## Core Ideas' and '## Evolution / Contradictions'.
- "is_new": boolean (true if creating a new node, false if updating an existing node found in the index)
    
Use this current taxonomy context to route the file appropriately, or invent a new category if it doesn't fit:
${currentIndex.substring(0, 2000)}

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
    
    const lines = indexData.split('\n');
    const tree = {};
    let currentL1 = null, currentL2 = null, currentL3 = null;

    for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed === '# LLM-Wiki Catalog' || trimmed === '# Wiki Catalog') continue;
        if (trimmed.startsWith('#### ')) {
            currentL3 = trimmed.replace('#### ', '');
            if (!tree[currentL1][currentL2][currentL3]) tree[currentL1][currentL2][currentL3] = [];
        } else if (trimmed.startsWith('### ')) {
            currentL2 = trimmed.replace('### ', '');
            if (!tree[currentL1]) tree[currentL1] = {};
            if (!tree[currentL1][currentL2]) tree[currentL1][currentL2] = {};
            currentL3 = null;
        } else if (trimmed.startsWith('## ')) {
            currentL1 = trimmed.replace('## ', '');
            if (!tree[currentL1]) tree[currentL1] = {};
            currentL2 = null;
            currentL3 = null;
        } else if (trimmed.startsWith('- [[')) {
            if (currentL1 && currentL2 && currentL3) {
                if (!tree[currentL1][currentL2][currentL3].includes(trimmed)) {
                    tree[currentL1][currentL2][currentL3].push(trimmed);
                }
            }
        }
    }

    // Insert new entry
    if (!tree[data.l1]) tree[data.l1] = {};
    if (!tree[data.l1][data.l2]) tree[data.l1][data.l2] = {};
    if (!tree[data.l1][data.l2][data.l3]) tree[data.l1][data.l2][data.l3] = [];
    
    if (!tree[data.l1][data.l2][data.l3].includes(entry)) {
        tree[data.l1][data.l2][data.l3].push(entry);
    }

    let newContent = '# Wiki Catalog\n\n';
    for (const l1 of Object.keys(tree).sort()) {
        newContent += `## ${l1}\n`;
        for (const l2 of Object.keys(tree[l1]).sort()) {
            newContent += `### ${l2}\n`;
            for (const l3 of Object.keys(tree[l1][l2]).sort()) {
                newContent += `#### ${l3}\n`;
                for (const item of tree[l1][l2][l3].sort()) {
                    newContent += `${item}\n`;
                }
            }
        }
        newContent += '\n';
    }
    fs.writeFileSync(INDEX_FILE, newContent);
}

async function ingestFile(filePath, keep) {
    initDirectories();
    const rawPath = path.resolve(filePath);
    const content = fs.readFileSync(rawPath, 'utf8');

    console.log(`\nProcessing: ${path.basename(rawPath)}`);
    const data = await extractConcepts(content);
    const dateStr = new Date().toISOString().split('T')[0];
    const baseFileName = path.basename(rawPath, '.md');
    
    const nodePath = path.join(NODES_DIR, `${data.title}.md`);
    let nodeContent = "";

    if (!data.is_new && fs.existsSync(nodePath)) {
        console.log(`  -> Synthesizing into existing node: ${data.title}`);
        let existingContent = fs.readFileSync(nodePath, 'utf8');
        nodeContent = `---
Created: '${dateStr}'
Updated: '${dateStr}'
Tags: ['#concept', '#wiki']
---
# ${data.title}

${data.description}

${data.content}

## Sources
`;
        let sources = `- [[${baseFileName}]]\n`;
        const oldMatch = existingContent.match(/## Sources[\s\S]*/);
        if (oldMatch) {
            const oldSources = oldMatch[0].replace('## Sources', '').trim();
            if (!oldSources.includes(baseFileName)) {
                sources = oldSources + '\n' + sources;
            } else {
                sources = oldSources + '\n';
            }
        }
        nodeContent += sources;
    } else {
        console.log(`  -> Creating new node: ${data.title} (${data.l1} > ${data.l2} > ${data.l3})`);
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
        updateIndex(data, data.title);
    }

    fs.writeFileSync(nodePath, nodeContent);
    
    const logEntry = `\n## [${dateStr}] Ingest | ${baseFileName} | Touched: [[${data.title}]]`;
    fs.appendFileSync(LOG_FILE, logEntry);

    if (!keep) {
        const archivePath = path.join(config.RAW_ARCHIVE_DIR, path.basename(rawPath));
        fs.copyFileSync(rawPath, archivePath);
        fs.unlinkSync(rawPath);
    }
}

function findMarkdownFiles(dir, fileList = []) {
    const files = fs.readdirSync(dir);
    for (const file of files) {
        if (file.startsWith('.')) continue;
        const filePath = path.join(dir, file);
        if (fs.statSync(filePath).isDirectory()) {
            findMarkdownFiles(filePath, fileList);
        } else if (file.endsWith('.md')) {
            fileList.push(filePath);
        }
    }
    return fileList;
}

program.command('config')
    .description('Generate or update ~/.wiki.json')
    .option('--api-key <key>', 'Set OPENAI_API_KEY')
    .action((options) => {
        let cfg = loadConfig();
        if (options.apiKey) cfg.OPENAI_API_KEY = options.apiKey;
        fs.writeFileSync(CONFIG_PATH, JSON.stringify(cfg, null, 2));
        console.log(`Saved config to ${CONFIG_PATH}`);
    });

program.command('add <file>')
    .description('Ingest a raw file into the Wiki')
    .option('--keep', 'Do not move the raw file')
    .action(async (file, options) => {
        try {
            await ingestFile(file, options.keep);
            console.log('Complete.');
        } catch (e) {
            console.error('Error:', e.message);
        }
    });

program.command('batch <dir>')
    .description('Batch ingest all markdown files in a directory')
    .option('--keep', 'Do not move the raw files', true)
    .action(async (dir, options) => {
        try {
            const files = findMarkdownFiles(path.resolve(dir));
            console.log(`Found ${files.length} markdown files.`);
            for (const file of files) {
                try {
                    await ingestFile(file, options.keep);
                } catch (e) {
                    console.error(`  -> Failed to process ${file}: ${e.message}`);
                }
            }
            console.log('\nBatch complete.');
        } catch (e) {
            console.error('Error:', e.message);
        }
    });

program.command('lint').action(() => {
    initDirectories();
    const indexData = fs.readFileSync(INDEX_FILE, 'utf8');
    const nodes = fs.readdirSync(NODES_DIR).filter(f => f.endsWith('.md'));
    let orphans = nodes.filter(n => !indexData.includes(`[[${path.basename(n, '.md')}]]`));
    if (orphans.length > 0) console.log('⚠️ Orphans:', orphans);
    else console.log('✅ All nodes indexed.');
});

program.parse(process.argv);
