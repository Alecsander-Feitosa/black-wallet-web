from web3 import Web3
import json

# 1. Conectar ao Ganache local
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))

if not w3.is_connected():
    print("Erro: Não foi possível conectar ao Ganache.")
    exit()

print("✅ Conectado ao Ganache (Mainnet Fork)!\n")

# 2. Endereços importantes
# Contrato real do USDT na rede Ethereum principal
USDT_ADDRESS = w3.to_checksum_address('0xdAC17F958D2ee523a2206206994597C13D831ec7')
# Conta rica em USDT que desbloqueamos no Ganache (Binance 8)
RICH_ACCOUNT = w3.to_checksum_address('0xF977814e90dA44bFA03b6295A0616a897441aceC')

# 3. Criar uma nova carteira (Account)
nova_carteira = w3.eth.account.create()
MEU_ENDERECO = nova_carteira.address
MINHA_CHAVE_PRIVADA = nova_carteira.key.hex()

print("--- 🆕 NOVA CARTEIRA CRIADA ---")
print(f"Endereço: {MEU_ENDERECO}")
print(f"Chave Privada: {MINHA_CHAVE_PRIVADA}\n")

# 4. ABI mínimo do padrão ERC-20 (apenas o que precisamos)
erc20_abi = json.loads('''[
    {"constant":true,"inputs":[{"name":"who","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"},
    {"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[],"type":"function"}
]''')

# 5. Instanciar o contrato do USDT
usdt_contract = w3.eth.contract(address=USDT_ADDRESS, abi=erc20_abi)

# 6. Checar saldo inicial da nova carteira
saldo_inicial = usdt_contract.functions.balanceOf(MEU_ENDERECO).call()
print(f"Saldo Inicial da Nova Carteira: {saldo_inicial / 10**6} USDT") # USDT tem 6 casas decimais

# 7. Transferir USDT da conta rica para a nossa nova carteira
quantidade_transferir = 1000 * (10**6) # 1.000 USDT (ajustado para 6 casas decimais)

print("\n💸 Transferindo 1.000 USDT da Baleia para sua nova carteira...")

# Como a conta rica está "unlocked" no Ganache, não precisamos assinar com a chave privada dela!
tx_hash = usdt_contract.functions.transfer(MEU_ENDERECO, quantidade_transferir).transact({
    'from': RICH_ACCOUNT,
    'gas': 100000 # Limite de gas para a transferência de token
})

# Esperar a transação ser minerada
w3.eth.wait_for_transaction_receipt(tx_hash)
print("✅ Transferência concluída!\n")

# 8. Checar saldo final
saldo_final = usdt_contract.functions.balanceOf(MEU_ENDERECO).call()
print(f"💰 Saldo Final da Nova Carteira: {saldo_final / 10**6} USDT")