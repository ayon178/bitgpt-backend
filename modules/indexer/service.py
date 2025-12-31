import asyncio
import logging
from web3 import Web3
from eth_abi import decode
from modules.blockchain.model import SystemConfig
from modules.indexer.events import TOPIC_TO_EVENT_NAME
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BlockchainIndexer")

# Config
RPC_URL = "https://opbnb-mainnet-rpc.bnbchain.org"  # opBNB Mainnet
CONTRACT_ADDRESS = "0xYOUR_CONTRACT_ADDRESS_HERE"  # TODO: Update with deployed address
POLL_INTERVAL = 5  # Seconds
CHUNK_SIZE = 2000
SAFETY_LAG = 5  # Blocks to stay behind head to avoid reorgs

class BlockchainIndexer:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        self.contract_address = Web3.to_checksum_address(CONTRACT_ADDRESS)
        self.is_running = False

    async def start_worker(self):
        """Starts the background indexing loop."""
        self.is_running = True
        logger.info(f"🚀 Blockchain Indexer started for {self.contract_address} on opBNB")

        while self.is_running:
            try:
                await self.process_blocks()
            except Exception as e:
                logger.error(f"❌ Error in indexer loop: {e}")
            
            await asyncio.sleep(POLL_INTERVAL)

    async def process_blocks(self):
        """Fetches and processes logs from the last processed block to the current safety block."""
        
        # 1. Get current chain head
        current_opbnb_block = self.w3.eth.block_number
        target_block = current_opbnb_block - SAFETY_LAG

        # 2. Get last processed block from DB
        last_block = self._get_last_processed_block()
        
        # If fresh start (or DB empty), start from current - 100 or specific block
        if last_block == 0:
             last_block = target_block - 100 
             logger.info(f"⚠️ No last block found, starting from {last_block}")

        if last_block >= target_block:
            return  # Already up to date

        # 3. Process in chunks
        start_block = last_block + 1
        
        while start_block <= target_block:
            end_block = min(start_block + CHUNK_SIZE - 1, target_block)
            
            logger.info(f"🔍 Scanning blocks {start_block} to {end_block}...")
            
            try:
                logs = self.w3.eth.get_logs({
                    'fromBlock': start_block,
                    'toBlock': end_block,
                    'address': self.contract_address
                })
                
                for log in logs:
                    self._handle_log(log)
                
                # Update checkpoint
                self._update_last_processed_block(end_block)
                start_block = end_block + 1
                
            except Exception as e:
                logger.error(f"⚠️ Failed to fetch logs ({start_block}-{end_block}): {e}")
                # Don't advance start_block so it retries
                await asyncio.sleep(5)
                break

    def _handle_log(self, log):
        """Decodes and routes the log to the correct handler."""
        topic0 = log['topics'][0].hex()
        event_name = TOPIC_TO_EVENT_NAME.get(topic0)

        if not event_name:
            return

        try:
            # Decode logic (simplified for demonstration)
            # In a real app, you'd use contract.events[Name]().process_log(log) 
            # or manual eth_abi.decode based on the event signature.
            
            logger.info(f"✅ Event Detected: {event_name} - Tx: {log['transactionHash'].hex()}")
            
            # --- Handler Routing ---
            if event_name == 'Registered':
                self._handle_registered(log)
            elif event_name == 'SlotPurchased':
                self._handle_slot_purchased(log)
            elif event_name == 'Placed':
                self._handle_placed(log)
            elif event_name == 'LevelPayout':
                self._handle_income(log, "Level Income")
            
        except Exception as e:
            logger.error(f"Error processing log {log['transactionHash'].hex()}: {e}")

    # --- DB Helpers ---
    
    def _get_last_processed_block(self):
        """Fetches the last processed block number from SystemConfig."""
        config = SystemConfig.objects(config_key='indexer_last_block').first()
        if config:
            return int(config.config_value)
        return 0

    def _update_last_processed_block(self, block_num):
        """Updates the checkpoint in DB."""
        SystemConfig.objects(config_key='indexer_last_block').update_one(
            upsert=True,
            set__config_value=str(block_num),
            set__description="Last processed block by Blockchain Indexer",
            set__updated_at=datetime.utcnow()
        )

    # --- Event Handlers (Placeholders for now) ---

    def _handle_registered(self, log):
        # Decode data (user, referrer, code)
        # Update User collection in Mongo
        pass

    def _handle_slot_purchased(self, log):
        # Update SlotActivation
        pass

    def _handle_placed(self, log):
        # Update TreePlacement
        pass

    def _handle_income(self, log, reason):
        # Update WalletLedger
        pass
