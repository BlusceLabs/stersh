const path = require("path")
const HtmlWebpackPlugin = require("html-webpack-plugin")
const MiniCssExtractPlugin = require("mini-css-extract-plugin")
const ReactRefreshWebpackPlugin = require("@pmmmwh/react-refresh-webpack-plugin")
const Dotenv = require("dotenv-webpack")

const isDev = process.env.NODE_ENV !== "production"

module.exports = {
  mode: isDev ? "development" : "production",

  entry: "./src/main.tsx",

  output: {
    path: path.resolve(__dirname, "dist"),
    filename: isDev ? "[name].js" : "[name].[contenthash].js",
    chunkFilename: isDev ? "[name].chunk.js" : "[name].[contenthash].chunk.js",
    clean: true,
    publicPath: "/",
  },

  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
    extensions: [".tsx", ".ts", ".js", ".jsx"],
  },

  module: {
    rules: [
      {
        test: /\.tsx?$/,
        exclude: /node_modules/,
        use: {
          loader: "ts-loader",
          options: {
            transpileOnly: isDev,
          },
        },
      },
      {
        test: /\.css$/,
        use: [
          isDev ? "style-loader" : MiniCssExtractPlugin.loader,
          {
            loader: "css-loader",
            options: {
              importLoaders: 1,
            },
          },
          "postcss-loader",
        ],
      },
      {
        test: /\.(png|jpe?g|gif|svg|webp|mp4|woff2?)$/i,
        type: "asset/resource",
      },
    ],
  },

  plugins: [
    new HtmlWebpackPlugin({
      template: "./index.html",
    }),
    new Dotenv({
      path: path.resolve(__dirname, ".env"),
      defaults: true,
    }),
    ...(isDev
      ? [new ReactRefreshWebpackPlugin()]
      : [
          new MiniCssExtractPlugin({
            filename: "[name].[contenthash].css",
          }),
        ]),
  ],

  devServer: {
    port: process.env.PORT ? parseInt(process.env.PORT) : 5173,
    hot: true,
    historyApiFallback: true,
    client: {
      overlay: {
        errors: true,
        warnings: false,
      },
    },
    proxy: [
      {
        context: ["/api"],
        target: `http://localhost:${process.env.GATEWAY_PORT || 8080}`,
        changeOrigin: true,
      },
    ],
  },

  devtool: isDev ? "eval-source-map" : false,

  performance: {
    hints: false,
  },

  optimization: {
    splitChunks: {
      chunks: "all",
    },
  },
}
