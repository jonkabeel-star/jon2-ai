const http = require(“http”);

const PORT = process.env.PORT || 3000;

const server = http.createServer((req, res) => {
res.setHeader(“Content-Type”, “application/json; charset=utf-8”);
res.setHeader(“Access-Control-Allow-Origin”, “*”);
res.setHeader(“Access-Control-Allow-Methods”, “GET, POST, OPTIONS”);
res.setHeader(“Access-Control-Allow-Headers”, “Content-Type”);

if (req.method === “OPTIONS”) {
res.writeHead(204);
return res.end();
}

if (req.url === “/api/health” && req.method === “GET”) {
res.writeHead(200);
return res.end(JSON.stringify({
project: “Jon2 AI”,
status: “online”,
message: “Jon2 AI server is running”
}));
}

res.writeHead(404);
res.end(JSON.stringify({
error: “Endpoint not found”
}));
});

server.listen(PORT, “0.0.0.0”, () => {
console.log(Jon2 AI server listening on port ${PORT});
});
