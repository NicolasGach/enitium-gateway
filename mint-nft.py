from web3 import Web3

w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

with open("data.json", 'r') as f:
    datastore = json.load(f)
    abi = datastore["abi"]
    contract_address = datastore["contract_address"]

w3.eth.defaultAccount = w3.eth.accounts[1]

