const express = require('express');
const path = require('path');

module.exports = function mountPublicAssets(app, root) {
  for (const dir of ['js', 'css', 'img', 'font']) {
    app.use(`/${dir}`, express.static(path.join(root, dir), { dotfiles: 'deny' }));
  }
  const files = [
    'config/style.js',
    'data/data_basic.js',
    'data/data_price.js',
    'data/data.js',
    'data/data_logistics.js',
    'data/data_bookmarks.js',
    'data/warehouse_data.js',
  ];
  for (const file of files) {
    app.get(`/${file}`, (req, res) => res.sendFile(path.join(root, file)));
  }
};
