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
from bot.handlers import start, create, group_roles, group_actions, admin
from bot.utils.telegram_client import UserClient
from loguru import logger


class EscrowBot:
    """Main escrow bot class."""
    
    def __init__(self):
        self.bot = None
        self.dp = None
        self.user_client = None
        self.health_task = None
    
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
            self.dp.include_router(create.router)
            self.dp.include_router(group_roles.router)
            self.dp.include_router(group_actions.router)
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
            BotCommand(command="start", description="Show welcome menu"),
            BotCommand(command="create", description="Create a new escrow group"),
            BotCommand(command="seller", description="Declare seller role with wallet (in group)"),
            BotCommand(command="buyer", description="Declare buyer role with wallet (in group)"),
            BotCommand(command="reset", description="Reset role declarations (in group)"),
            BotCommand(command="qr", description="Get QR code of escrow address (in group)"),
            BotCommand(command="balance", description="Check deposit status (in group)"),
            BotCommand(command="pay_seller", description="Release funds to seller (buyer only, in group)"),
            BotCommand(command="refund_buyer", description="Refund buyer — admin only"),
            BotCommand(command="contact", description="Contact arbitrator / raise dispute (in group)"),
        ]
        await self.bot.set_my_commands(commands)
    
    async def run(self):
        """Run the bot."""
        try:
            logger.info("🤖 Starting bot polling...")
            self.health_task = asyncio.create_task(self.health_monitor())
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"❌ Bot error: {e}")
        finally:
            await self.shutdown()

    async def health_monitor(self):
        """Emit a periodic heartbeat and try to recover MongoDB connectivity."""
        while True:
            try:
                await asyncio.sleep(settings.heartbeat_interval_seconds)

                db = MongoDB.get_db()
                await db.command("ping")

                telethon_status = "connected" if self.user_client else "disabled"
                logger.info(f"Heartbeat ok | db=connected | telethon={telethon_status}")
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(f"Heartbeat detected degraded state: {e}")

                try:
                    await MongoDB.connect_db()
                    if self.dp is not None:
                        self.dp['db'] = MongoDB.get_db()
                    logger.info("MongoDB connection recovered during heartbeat")
                except Exception as reconnect_error:
                    logger.error(
                        f"MongoDB reconnect attempt failed during heartbeat: {reconnect_error}"
                    )
    
    async def shutdown(self):
        """Shutdown bot and close connections."""
        logger.info("🛑 Shutting down...")
        if self.health_task:
            self.health_task.cancel()
            try:
                await self.health_task
            except asyncio.CancelledError:
                pass
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
