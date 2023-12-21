#!/usr/bin/env node
"use strict";
// curl -X POST -d 'url=https://www.ntta.org/sites/default/files/2022-07/FY2022-Final-System-Budget.pdf' http://127.0.0.1:3000/api/v1/conv

const fs = require("fs");
const PDFParser = require("pdf2json");
const axios = require("axios");
const express = require("express");
const bodyParser = require("body-parser");
const crypt = require("crypto");
const StringifyStream = require("stringifystream");

const app = express();
app.use(bodyParser.urlencoded({ extended: true }));
app.use(express.json());

const pdfParser = new PDFParser();

async function getPdfFromUrl(url) {
  try {
    console.log("Downloading " + url);
    const response = await axios.get(url, { responseType: "arraybuffer" });
    const pdfContents = response.data;
    const hash = crypt.createHash("sha256");
    const hashValue = hash.update(pdfContents).digest("hex");
    // pdfParser.loadPDF(hashValue + ".pdf");
    const inputStream = fs.createReadStream(hashValue + ".pdf", {
      bufferSize: 64 * 1024,
    });
    const outputStream = fs.createWriteStream(hashValue + ".json");
    inputStream
      .pipe(pdfParser.createParserStream())
      .pipe(new StringifyStream())
      .pipe(outputStream);
    const jsonFile = fs.readSync(hashValue + ".json");
    return jsonFile;
  } catch (error) {
    console.error(url + ":" + error);
  }
}

app.post("/api/v1/conv", async (req, res) => {
  const pdfURL = req.body.url;
  console.log(pdfURL);
  const jsonFile = await getPdfFromUrl(pdfURL);
  res.send({ jsonFile });
});

const port = process.env.SERVER_LISTEN_PORT || 3000;
app.listen(port, () => {
  console.log("Server is running on port " + port);
});
