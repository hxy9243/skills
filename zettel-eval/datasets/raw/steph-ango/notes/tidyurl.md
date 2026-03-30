Tidy URL removes unnecessary cruft in URLs such as UTM parameters and copies the link to your clipboard. This removes tracking info and makes links nicer to share.

To install Tidy URL, simply drag the `TidyURL` link below into your bookmarks. Then click the bookmark to get a tidy URL and copy it to your clipboard.

TidyURL

- [[tidy|Tidy Reader]] my bookmarklet for making web pages more readable.
- [[obsidian-web-clipper|Obsidian Web Clipper]] for saving web pages to [[obsidian|Obsidian]].

## Code

```js
javascript:(function(){
  const url = window.location.href;
  const tidyUrl = url.split('?')[0];
  navigator.clipboard.writeText(tidyUrl).then(function() {
    window.location.href = tidyUrl;
  }).catch(function() {
    window.location.href = tidyUrl;
  });
})();
```
