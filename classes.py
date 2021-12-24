from web3 import Web3

class W3EnitiumContract:

    def __init__(self, provider, contract_address, contract_abi):
        self.w3 = Web3(Web3.HTTPProvider(provider))
        self.contract = w3.eth.contract(address=contract_address, abi=contract_abi)
    
    def burn(tokenId):
        pass
