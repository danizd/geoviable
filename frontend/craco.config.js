const path = require('path');

module.exports = {
  webpack: {
    alias: {
      // Force ALL modules to use the SAME Leaflet instance
      leaflet: path.resolve(__dirname, 'node_modules/leaflet'),
    },
    configure: (webpackConfig) => {
      // Ensure leaflet is resolved to a single instance
      webpackConfig.resolve.alias = {
        ...webpackConfig.resolve.alias,
        leaflet: path.resolve(__dirname, 'node_modules/leaflet'),
      };
      return webpackConfig;
    },
  },
};
