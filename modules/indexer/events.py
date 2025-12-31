from web3 import Web3

# Event signatures from Binary.sol
EVENT_SIGNATURES = {
    'Registered': 'Registered(address,address,bytes32)',
    'Placed': 'Placed(address,uint256,address,bool)',
    'SlotPurchased': 'SlotPurchased(address,uint8,uint256)',
    'AutoUpgraded': 'AutoUpgraded(address,uint8,uint256,uint256)',
    'LevelPayout': 'LevelPayout(address,address,uint8,uint8,uint256)',
    'PartnerIncentive': 'PartnerIncentive(address,address,uint8,uint256)',
    'PoolFunded': 'PoolFunded(address,uint8,string,uint256,address)'
}

# Pre-compute topics
EVENT_TOPICS = {
    name: Web3.keccak(text=sig).hex()
    for name, sig in EVENT_SIGNATURES.items()
}

# Reverse mapping for easy lookup
TOPIC_TO_EVENT_NAME = {
    topic: name
    for name, topic in EVENT_TOPICS.items()
}
