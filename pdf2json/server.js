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

async function getPdfFromUrl(url) {
  try {
    const response = await axios.get(url, { responseType: "arraybuffer" });
    const pdfContents = response.data;
    const hash = crypt.createHash("sha256");
    const hashValue = hash.update(pdfContents).digest("hex");

    fs.writeFileSync(hashValue + ".pdf", pdfContents, "binary");

    const pdfParser = new PDFParser();
    const inputStream = fs.createReadStream(hashValue + ".pdf", {
      bufferSize: 64 * 1024,
    });
    const outputStream = fs.createWriteStream(hashValue + ".json");
    inputStream
      .pipe(pdfParser.createParserStream())
      .pipe(new StringifyStream())
      .pipe(outputStream);
    return hashValue;
  } catch (error) {
    console.error(url + ":" + error);
  }
}

app.post("/api/v1/conv", async (req, res) => {
  const pdfURL = req.body.url;
  const pdfHash = await getPdfFromUrl(pdfURL);
  const data = fs.readFileSync(pdfHash + ".json", "utf8");
  const jsonData = JSON.parse(data);
  const transformedData = JSON.stringify(jsonData);
  res.header("Content-Type", "application/json");
  res.json({ transformedData });
});

const port = process.env.SERVER_LISTEN_PORT || 3000;
app.listen(port, () => {
  console.log("Server is running on port " + port);
});
