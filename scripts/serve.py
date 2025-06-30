#!/usr/bin/env python3

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from inference.server import run_server


def main():
    parser = argparse.ArgumentParser(description="Serve job search model")
    parser.add_argument("--trained-model", type=str, default=None,
                       help="Path to trained model (optional, uses base model if not provided)")
    parser.add_argument("--port", type=int, default=8000,
                       help="Port to serve on (default: 8000)")
    parser.add_argument("--host", type=str, default="0.0.0.0",
                       help="Host to serve on (default: 0.0.0.0)")
    
    args = parser.parse_args()
    
    model_type = "🎯 Trained Model" if args.trained_model else "📱 Base Model"
    print(f"🚀 Starting MCP Job Search Server ({model_type})...")
    print("📝 Server will be available at:")
    print(f"   - Main API: http://localhost:{args.port}")
    print(f"   - Chatbox UI: http://localhost:{args.port}/chatbox")
    print(f"   - WebSocket: ws://localhost:{args.port}/ws/{{user_id}}")
    if args.trained_model:
        print(f"   - Model: {args.trained_model}")
    print(
        f"\n💡 To test the chatbox, open http://localhost:{args.port}/chatbox in your browser"
    )
    print(f"📱 Or send POST requests to http://localhost:{args.port}/search_jobs")
    print("\n⚡ Starting server...")

    try:
        run_server(host=args.host, port=args.port, trained_model_path=args.trained_model)
    except KeyboardInterrupt:
        print("\n👋 Server stopped gracefully")
    except Exception as e:
        print(f"\n❌ Server error: {e}")


if __name__ == "__main__":
    main()
