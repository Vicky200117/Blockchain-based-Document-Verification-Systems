module.exports = {
  networks: {
    development: {
      host: "127.0.0.1",     // Localhost (default: none)
      port: 7545,            // Standard Ganache port (default: none)
      network_id: "5777",       // Any network (default: none)
    }
  },

  compilers: {
    solc: {
      version: "0.8.0",    // Specify the compiler version
      settings: {
        optimizer: {
          enabled: false,
          runs: 200
        },
        evmVersion: "istanbul"
      }
    }
  },

  db: {
    enabled: false
  }
};
