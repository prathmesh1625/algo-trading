import uvicorn

if __name__ == "__main__":
    uvicorn.run("youtube_summarizer.main:app", host="0.0.0.0", port=8000, reload=True)
