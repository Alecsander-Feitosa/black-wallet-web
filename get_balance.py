from web3 import Web3
import json

w3 = Web3(Web3.HTTPProvider('https://eth.llamarpc.com'))
erc20_abi = json.loads('[{"constant":true,"inputs":[{"name":"who","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"}]')
contract = w3.eth.contract(address=w3.to_checksum_address('0xdac17f958d2ee523a2206206994597c13d831ec7'), abi=erc20_abi)
balance = contract.functions.balanceOf(w3.to_checksum_address('0x3fe705e2ffcaee8d7287de047def35db3e794c76')).call()
print(balance / 10**6)
