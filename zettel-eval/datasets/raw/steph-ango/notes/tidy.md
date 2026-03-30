Tidy is a simple [open source](https://github.com/kepano/tidy) bookmarklet that uses [[defuddle|Defuddle]] to tidy up web pages for easy reading.

To install Tidy, simply drag the “Tidy!” link below into your bookmarks. Then click the bookmark to clean up an article page.

Tidy

## Troubleshooting

This bookmarklet may not work on all websites and browsers. You can troubleshoot issues by opening the Developer Console in your browser and checking if any errors appear when you click the bookmarklet.

The most common error is that a website or the browser itself is blocking third party code execution. This is commonly due to the `connect-src` Content Security Policy (CSP) used by some websites.

- [[obsidian-web-clipper|Obsidian Web Clipper]] for saving web pages to [[obsidian|Obsidian]].
- [[tidyurl|Tidy URL]] my bookmarklet that cleans up URLs to make them more shareable.

## Code

```js
javascript: (function() {
    console.log('start');
    var jsCode = document.createElement('script');
    jsCode.setAttribute('src', 'https://unpkg.com/defuddle@latest/dist/index.js');
    window.tidyHtml = (function() {
        var article = new Defuddle(document).parse();
        document.children[0].innerHTML = article.content;
        var styles = \`@media (prefers-color-scheme: dark) {:root {--background: #222;--text: white;--text-muted: #999;}}@media (prefers-color-scheme: light) {:root {--background: white;--text: black;--text-muted: #666;}}* {font-family: -apple-system, BlinkMacSystemFont, "Inter", "IBM Plex Sans", Segoe UI, Helvetica, Arial, sans-serif, Apple Color Emoji, Segoe UI Emoji, Segoe UI Symbol;}code, pre {font-family: IBM Plex Mono, monospace;font-size: calc(1rem + 0.5vw);}html {box-sizing: border-box;width: 100%;height: 100%;font-size: 62.5%;background-color: var(--background) !important;}body {font-size: calc(1.6rem + 0.5vw);line-height: 1.8;margin: 0 auto;width: 40em;max-width: 88%;color: var(--text);background-color: var(--background);}.page {margin: 2rem auto;background: var(--background);padding: 0 0 20rem 0;}h1 {font-size: 44px !important;letter-spacing: -0.5px !important;line-height: 46px !important;margin: 22px 0 15px 0 !important;}h2 {font-size: 35px;line-height: 38px;font-weight: bold;}h3 {font-size: inherit;font-weight: bold;border-bottom: 1px solid #333;}ul {margin: 1rem;}ol {margin: 1rem;}video, img {max-width: 100%;}a {color: var(--text);text-decoration: underline;}a:visited {opacity: 0.6;color: var(--text-muted);}blockquote {margin: 0;padding: 0.1em 0 0.1em 2em;border-left: 2px solid #ccc;color: var(--text-muted);}pre {background-color: #ccc;padding: 1rem;}code {color: var(--text-muted);}pre > code {color: #333;}\`
        var tidyStyle = document.createElement("style")
        tidyStyle.innerText = styles
        document.head.appendChild(tidyStyle)
    });
    jsCode.onload = tidyHtml;
    document.body.appendChild(jsCode);
}());
```
