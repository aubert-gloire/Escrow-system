"""
On-chain transaction verifier for BTC, ETH, LTC, USDT (TRC20).
Uses free public APIs — no blockchain node required.

APIs used:
  BTC  — mempool.space        (no key needed)
  LTC  — blockcypher.com      (optional token for higher rate limits)
  ETH  — etherscan.io         (free API key required: ETHERSCAN_API_KEY)
  USDT — tronscan.org TRC20   (no key needed)
"""

import aiohttp
from typing import Optional

from loguru import logger


def _ok(amount, confirmations, address_match, confirmed):
    return {
        "found": True,
        "confirmed": confirmed,
        "amount": amount,
        "confirmations": confirmations,
        "address_match": address_match,
        "error": None,
    }


def _err(msg):
    return {
        "found": False,
        "confirmed": False,
        "amount": None,
        "confirmations": None,
        "address_match": False,
        "error": msg,
    }


# ── BTC — mempool.space ───────────────────────────────────────────────────────

async def _verify_btc(tx_hash: str, expected_address: str) -> dict:
    timeout = aiohttp.ClientTimeout(total=12)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.get(f"https://mempool.space/api/tx/{tx_hash}") as r:
                if r.status == 404:
                    return _err("Transaction not found on chain yet (may be unconfirmed).")
                if r.status != 200:
                    return _err(f"mempool.space returned HTTP {r.status}.")
                tx = await r.json()

            amount_sat = sum(
                out["value"]
                for out in tx.get("vout", [])
                if out.get("scriptpubkey_address") == expected_address
            )
            address_match = amount_sat > 0
            amount_btc = amount_sat / 1e8

            status = tx.get("status", {})
            confirmed = bool(status.get("confirmed"))
            block_height = status.get("block_height")
            confirmations = 0

            if confirmed and block_height:
                async with s.get("https://mempool.space/api/blocks/tip/height") as r2:
                    if r2.status == 200:
                        tip = int(await r2.text())
                        confirmations = tip - block_height + 1

        return _ok(
            amount=round(amount_btc, 8) if address_match else None,
            confirmations=confirmations,
            address_match=address_match,
            confirmed=confirmed,
        )
    except Exception as e:
        logger.warning(f"BTC verify error: {e}")
        return _err(str(e))


# ── LTC — blockcypher ────────────────────────────────────────────────────────

async def _verify_ltc(tx_hash: str, expected_address: str, token: Optional[str]) -> dict:
    url = f"https://api.blockcypher.com/v1/ltc/main/txs/{tx_hash}"
    if token:
        url += f"?token={token}"
    timeout = aiohttp.ClientTimeout(total=12)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.get(url) as r:
                if r.status == 404:
                    return _err("Transaction not found on chain yet.")
                if r.status == 429:
                    return _err("BlockCypher rate limit hit — add BLOCKCYPHER_TOKEN to .env.")
                if r.status != 200:
                    return _err(f"BlockCypher returned HTTP {r.status}.")
                data = await r.json()

        amount_lits = sum(
            out["value"]
            for out in data.get("outputs", [])
            if expected_address in out.get("addresses", [])
        )
        address_match = amount_lits > 0
        amount_ltc = amount_lits / 1e8
        confirmations = data.get("confirmations", 0)
        confirmed = confirmations >= 1

        return _ok(
            amount=round(amount_ltc, 8) if address_match else None,
            confirmations=confirmations,
            address_match=address_match,
            confirmed=confirmed,
        )
    except Exception as e:
        logger.warning(f"LTC verify error: {e}")
        return _err(str(e))


# ── ETH — etherscan ───────────────────────────────────────────────────────────

async def _verify_eth(tx_hash: str, expected_address: str, api_key: str) -> dict:
    if not api_key:
        return _err("ETHERSCAN_API_KEY not set — add it to your .env to verify ETH.")

    base = "https://api.etherscan.io/api"
    timeout = aiohttp.ClientTimeout(total=12)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.get(
                f"{base}?module=proxy&action=eth_getTransactionByHash"
                f"&txhash={tx_hash}&apikey={api_key}"
            ) as r:
                tx_data = await r.json()

            tx = tx_data.get("result")
            if not tx or tx == "Transaction not found":
                return _err("Transaction not found on chain yet.")

            to_address = (tx.get("to") or "").lower()
            address_match = to_address == expected_address.lower()
            amount_eth = int(tx["value"], 16) / 1e18

            tx_block = tx.get("blockNumber")
            confirmations = 0
            confirmed = False

            if tx_block:
                async with s.get(
                    f"{base}?module=proxy&action=eth_blockNumber&apikey={api_key}"
                ) as r2:
                    block_data = await r2.json()
                current_block = int(block_data["result"], 16)
                tx_block_num = int(tx_block, 16)
                confirmations = current_block - tx_block_num + 1
                confirmed = confirmations >= 1

        return _ok(
            amount=round(amount_eth, 8) if address_match else None,
            confirmations=confirmations,
            address_match=address_match,
            confirmed=confirmed,
        )
    except Exception as e:
        logger.warning(f"ETH verify error: {e}")
        return _err(str(e))


# ── USDT TRC20 — tronscan ────────────────────────────────────────────────────

# Official USDT contract on TRON mainnet
_USDT_TRC20_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"


async def _verify_usdt_trc20(tx_hash: str, expected_address: str) -> dict:
    url = f"https://apilist.tronscan.org/api/transaction-info?hash={tx_hash}"
    timeout = aiohttp.ClientTimeout(total=15)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.get(url, headers={"User-Agent": "Mozilla/5.0"}) as r:
                if r.status != 200:
                    return _err(f"TronScan returned HTTP {r.status}.")
                data = await r.json()

        if not data.get("hash"):
            return _err("Transaction not found on chain yet.")

        confirmed = bool(data.get("confirmed"))
        confirmations = 1 if confirmed else 0
        amount = 0.0
        address_match = False

        # TRC20 token transfers (USDT is TRC20)
        for t in data.get("trc20TransferInfo", []):
            if (
                t.get("to_address") == expected_address
                and t.get("contract_address") == _USDT_TRC20_CONTRACT
            ):
                amount += int(t.get("amount_str", "0")) / 1e6
                address_match = True

        # Fallback: TRC10 / legacy tokenTransferInfo
        if not address_match:
            ti = data.get("tokenTransferInfo") or {}
            if isinstance(ti, dict) and ti.get("to_address") == expected_address:
                decimals = int(ti.get("decimals", 6))
                amount = int(ti.get("amount_str", "0")) / (10 ** decimals)
                address_match = True

        return _ok(
            amount=round(amount, 6) if address_match else None,
            confirmations=confirmations,
            address_match=address_match,
            confirmed=confirmed,
        )
    except Exception as e:
        logger.warning(f"USDT TRC20 verify error: {e}")
        return _err(str(e))


# ── Public interface ──────────────────────────────────────────────────────────

async def verify_transaction(
    currency: str,
    tx_hash: str,
    expected_address: str,
    etherscan_api_key: Optional[str] = None,
    blockcypher_token: Optional[str] = None,
) -> dict:
    """
    Verify a transaction on-chain.

    Returns:
        found (bool)         — tx exists on chain
        confirmed (bool)     — at least 1 confirmation
        amount (float|None)  — amount received at expected_address (None if address mismatch)
        confirmations (int)  — number of confirmations
        address_match (bool) — funds actually went to expected_address
        error (str|None)     — set when the API call failed
    """
    currency = currency.upper()
    if currency == "BTC":
        return await _verify_btc(tx_hash, expected_address)
    if currency == "LTC":
        return await _verify_ltc(tx_hash, expected_address, blockcypher_token)
    if currency == "ETH":
        return await _verify_eth(tx_hash, expected_address, etherscan_api_key or "")
    if currency == "USDT":
        return await _verify_usdt_trc20(tx_hash, expected_address)
    return _err(f"Unsupported currency: {currency}")
