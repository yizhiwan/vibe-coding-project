(function () {
  const watchedFiles = ['index.html', 'styles.css', 'script.js'];
  const cache = {};

  async function getLastModified(file) {
    try {
      const response = await fetch(file, { method: 'HEAD' });
      return response.headers.get('Last-Modified');
    } catch (error) {
      return null;
    }
  }

  async function checkForChanges() {
    for (const file of watchedFiles) {
      const modified = await getLastModified(file);
      if (!modified) continue;

      if (cache[file] && cache[file] !== modified) {
        window.location.reload();
        return;
      }

      cache[file] = modified;
    }
  }

  (async function init() {
    for (const file of watchedFiles) {
      cache[file] = await getLastModified(file);
    }

    console.log('Live reload enabled');
    setInterval(checkForChanges, 1000);
  })();
})();
