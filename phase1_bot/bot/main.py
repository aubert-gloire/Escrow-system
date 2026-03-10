"""
Main Bot Entry Point - Phase 1
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from config.settings import settings, ensure_log_directory
from database.mongo import MongoDB
from bot.handlers import start, role, escrow, deposit, delivery, dispute, mydeals, admin
from bot.utils.telegram_client import UserClient
from loguru import logger


class EscrowBot:
    """Main escrow bot class."""
    
    def __init__(self):
        self.bot = None
        self.dp = None
        self.user_client = None
    
    async def setup(self):
        """Setup bot and database."""
        try:
            # Setup logging
            ensure_log_directory()
            logger.add(
                settings.log_file,
                rotation="500 MB",
                retention="7 days",
                level=settings.log_level
            )
            
            logger.info("=" * 60)
            logger.info("🔒 Starting Escrow Bot Phase 1")
            logger.info("=" * 60)
            
            # Connect to MongoDB
            await MongoDB.connect_db()

            # Connect Telethon user client (needed for group creation)
            self.user_client = await UserClient.connect()

            # Setup bot
            self.bot = Bot(token=settings.telegram_bot_token)
            self.dp = Dispatcher()

            # Inject DB and user client into dispatcher so handlers receive them
            self.dp['db'] = MongoDB.get_db()
            self.dp['user_client'] = self.user_client
            
            # Register handlers
            self.dp.include_router(start.router)
            self.dp.include_router(role.router)
            self.dp.include_router(escrow.router)
            self.dp.include_router(deposit.router)
            self.dp.include_router(delivery.router)
            self.dp.include_router(dispute.router)
            self.dp.include_router(mydeals.router)
            self.dp.include_router(admin.router)
            
            # Set bot commands
            await self.set_bot_commands()
            
            logger.info("✅ Bot setup complete")
            
        except Exception as e:
            logger.error(f"❌ Setup failed: {e}")
            raise
    
    async def set_bot_commands(self):
        """Set bot commands."""
        commands = [
            BotCommand(command="start", description="Start the bot"),
            BotCommand(command="seller", description="Register as seller"),
            BotCommand(command="buyer", description="Register as buyer"),
            BotCommand(command="escrow", description="Create escrow deal (buyer)"),
            BotCommand(command="join_deal", description="Join a deal as seller"),
            BotCommand(command="confirm_deposit", description="Submit deposit TX hash"),
            BotCommand(command="delivered", description="Mark deal as delivered (seller)"),
            BotCommand(command="complete_deal", description="Confirm receipt & complete (buyer)"),
            BotCommand(command="mydeals", description="View your deals"),
            BotCommand(command="help", description="Show help"),
        ]
        await self.bot.set_my_commands(commands)
    
    async def run(self):
        """Run the bot."""
        try:
            logger.info("🤖 Starting bot polling...")
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"❌ Bot error: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown bot and close connections."""
        logger.info("🛑 Shutting down...")
        if self.bot:
            await self.bot.session.close()
        await UserClient.disconnect()
        await MongoDB.close_db()
        logger.info("✅ Shutdown complete")


async def main():
    """Main entry point."""
    bot = EscrowBot()
    await bot.setup()
    await bot.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)
