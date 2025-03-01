# BackYT: AI-Powered YouTube Video Note Generator

<img alt="BackYT Logo" src="https://via.placeholder.com/150?text=BackYT">

## Overview

BackYT is an intelligent web application that helps you extract, organize, and interact with content from YouTube videos. Convert videos into structured notes, search through transcripts, and ask questions about video content - all powered by AI.

## Features

- **📝 Automated Notes Generation**: Convert YouTube videos into well-structured, readable notes
- **🔎 Semantic Search**: Find relevant information across your saved video notes
- **💬 Q&A Capability**: Ask questions about video content and get AI-generated answers
- **📂 Organization**: Create folders to organize your video notes efficiently
- **🔄 Real-time Updates**: Edit and update your notes with a rich text editor
- **🔒 Secure Authentication**: Google OAuth integration for seamless access

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Next.js (React)
- **Database**: PostgreSQL
- **Vector Database**: Pinecone
- **AI Models**: OpenAI GPT-4o-mini, Embeddings API
- **Authentication**: OAuth 2.0 (Google)

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL
- Pinecone account
- OpenAI API key

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/backyt.git
   cd backyt
   ```

2. **Set up the backend**

   ```bash
   # Create and activate virtual environment
   python -m venv ytnote
   source ytnote/bin/activate  # On Windows: ytnote\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt

   # Set up environment variables
   cp .env.example .env
   # Edit .env with your API keys and database details
   ```

3. **Set up the database**

   ```bash
   alembic upgrade head
   ```

4. **Start the backend server**

   ```bash
   uvicorn app.main:app --reload
   ```

5. **Set up the frontend**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Usage

1. **Sign in** using your Google account
2. **Create folders** to organize your content
3. **Add YouTube videos** by pasting URLs
4. **Generate notes** automatically from video transcripts
5. **Search and browse** your collection
6. **Ask questions** about specific video content

## API Documentation

API documentation is available at `/docs` or `/redoc` when the server is running.

## Architecture

<img alt="Architecture Diagram" src="https://via.placeholder.com/800x400?text=Architecture+Diagram">

- FastAPI handles backend requests and AI processing
- Vector embeddings stored in Pinecone for semantic search
- PostgreSQL manages user data, folders, and notes metadata
- Next.js frontend provides responsive UI with real-time updates

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI for AI models
- Pinecone for vector database
- YouTube API for video metadata

Made with ❤️ by [Akash Yadav]
