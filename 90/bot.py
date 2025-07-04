import os
import requests
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp
import tempfile
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
TOKEN = os.getenv("BOT_TOKEN")

class TikTokDownloader:
    def __init__(self):
        self.ydl_opts = {
            'format': 'best[ext=mp4]',
            'outtmpl': '%(title)s.%(ext)s',
            'no_warnings': True,
            'extractaudio': False,
            'audioformat': 'mp3',
            'embed_subs': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
        }
    
    def download_video(self, url, output_path):
        """Download TikTok video using yt-dlp"""
        try:
            self.ydl_opts['outtmpl'] = os.path.join(output_path, '%(title)s.%(ext)s')
            
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                # Extract video info
                info = ydl.extract_info(url, download=False)
                video_title = info.get('title', 'TikTok_Video')
                
                # Download the video
                ydl.download([url])
                
                # Find the downloaded file
                for file in os.listdir(output_path):
                    if file.endswith('.mp4'):
                        return os.path.join(output_path, file), video_title
                        
        except Exception as e:
            logger.error(f"Error downloading video: {str(e)}")
            return None, None
    
    def is_tiktok_url(self, url):
        """Check if URL is a valid TikTok URL"""
        tiktok_domains = ['tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com']
        return any(domain in url.lower() for domain in tiktok_domains)

# Initialize downloader
downloader = TikTokDownloader()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued"""
    welcome_message = """
🎵 *TikTok Video Downloader Bot* 🎵

Welcome! I can help you download TikTok videos.

*How to use:*
1. Send me a TikTok video URL
2. I'll download and send you the video

*Supported formats:*
- https://www.tiktok.com/@username/video/1234567890
- https://vm.tiktok.com/xxxxx
- https://vt.tiktok.com/xxxxx

*Commands:*
/start - Show this message
/help - Show help information

Just send me a TikTok URL and I'll do the rest! 🚀
    """
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued"""
    help_message = """
*Help - TikTok Video Downloader Bot*

*How to download TikTok videos:*
1. Copy the TikTok video URL from the TikTok app or website
2. Send the URL to this bot
3. Wait for the bot to process and download the video
4. The bot will send you the downloaded video

*Supported URL formats:*
- https://www.tiktok.com/@username/video/1234567890
- https://vm.tiktok.com/xxxxx
- https://vt.tiktok.com/xxxxx

*Tips:*
- Make sure the TikTok video is public
- The bot may take a few seconds to process longer videos
- If download fails, try again or check if the URL is correct

*Commands:*
/start - Welcome message
/help - This help message

*Note:* This bot respects TikTok's terms of service and only downloads publicly available content.
    """
    await update.message.reply_text(help_message, parse_mode='Markdown')

async def download_tiktok_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle TikTok URL and download video"""
    url = update.message.text.strip()
    
    # Check if it's a TikTok URL
    if not downloader.is_tiktok_url(url):
        await update.message.reply_text(
            "❌ Please send a valid TikTok URL.\n\n"
            "Supported formats:\n"
            "• https://www.tiktok.com/@username/video/1234567890\n"
            "• https://vm.tiktok.com/xxxxx\n"
            "• https://vt.tiktok.com/xxxxx"
        )
        return
    
    # Send processing message
    processing_message = await update.message.reply_text("🔄 Processing your TikTok video... Please wait.")
    
    try:
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download video
            video_path, video_title = downloader.download_video(url, temp_dir)
            
            if video_path and os.path.exists(video_path):
                # Check file size (Telegram has a 50MB limit for bots)
                file_size = os.path.getsize(video_path)
                if file_size > 50 * 1024 * 1024:  # 50MB
                    await processing_message.edit_text(
                        "❌ Video is too large to send via Telegram (>50MB).\n"
                        "Please try a shorter video."
                    )
                    return
                
                # Send video
                await processing_message.edit_text("📤 Uploading video...")
                
                with open(video_path, 'rb') as video_file:
                    await update.message.reply_video(
                        video=video_file,
                        caption=f"🎵 *{video_title}*\n\n✅ Downloaded successfully!",
                        parse_mode='Markdown'
                    )
                
                # Delete processing message
                await processing_message.delete()
                
            else:
                await processing_message.edit_text(
                    "❌ Failed to download video. Please check:\n"
                    "• The URL is correct\n"
                    "• The video is public\n"
                    "• The video still exists\n\n"
                    "Try again or contact support if the issue persists."
                )
                
    except Exception as e:
        logger.error(f"Error in download_tiktok_video: {str(e)}")
        await processing_message.edit_text(
            "❌ An error occurred while downloading the video.\n"
            "Please try again later or contact support."
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all text messages"""
    message_text = update.message.text.strip()
    
    # Check if message contains a URL
    if any(keyword in message_text.lower() for keyword in ['http', 'tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com']):
        await download_tiktok_video(update, context)
    else:
        await update.message.reply_text(
            "👋 Hi! Send me a TikTok video URL and I'll download it for you.\n\n"
            "Use /help for more information."
        )

def main():
    """Start the bot"""
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Run the bot until the user presses Ctrl-C
    print("🤖 TikTok Downloader Bot is starting...")
    print("Press Ctrl+C to stop the bot")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()