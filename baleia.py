from web3 import Web3
import json

# Conexão com o Ganache
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))

# Endereços do ecossistema
USDT_CONTRACT = w3.to_checksum_address('0xdAC17F958D2ee523a2206206994597C13D831ec7')
BALEIA_BINANCE = w3.to_checksum_address('0xF977814e90dA44bFA03b6295A0616a897441aceC')

# O endereço que você gerou na sua carteira
MINHA_CARTEIRA = w3.to_checksum_address('0x32F036bE2ddc89857C3487D2c6c9f7F5dbefB547')

# ABI mínima para transferência
abi = json.loads('[{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[],"type":"function"}]')
contrato = w3.eth.contract(address=USDT_CONTRACT, abi=abi)

# 27 milhões de dólares
quantidade = 27_654_983

print(f"💰 Injetando ${quantidade:,} dólares na sua conta...")

# Executa a transferência da baleia para você
tx_hash = contrato.functions.transfer(
    MINHA_CARTEIRA, 
    quantidade * 10**6 # Ajuste das 6 casas decimais do USDT
).transact({'from': BALEIA_BINANCE})

w3.eth.wait_for_transaction_receipt(tx_hash)

print(f"🚀 Status: MILIONÁRIO! Saldo atualizado no Ganache.")
print(f"Hash da Transação: {tx_hash.hex()}")