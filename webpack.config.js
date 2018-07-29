var webpack = require("webpack");
var path = require("path");


var config = {
    entry: {
        index: "./site/js/all.js",
    },
    output: {
        path: path.join(__dirname, "site/static"),
        filename: "site.js"
    },
    module: {
        loaders: [
            {
                test: /\.js$/,
                exclude: /node_modules/,
                loader: "babel",
                query: {
                    presets: ["env"],
                }
            },
        ]
    },
    plugins: [],
    resolve: {
        extensions: ['', '.js'],
    },
    devtool: 'source-map',
};

if (process.env.PROD_JS) {
    config.plugins.push(
        new webpack.DefinePlugin({"process.env": {NODE_ENV: JSON.stringify("production")}}),
        new webpack.optimize.DedupePlugin(),
        new webpack.optimize.UglifyJsPlugin({
            compress: {warnings: false},
        })
    );
}

module.exports = config;
