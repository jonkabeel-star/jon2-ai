import uvicorn
if __name__ == "__main__":
    uvicorn.run(
        "image_engine:app",
        host="0.0.0.0",
        port=8000
    )
