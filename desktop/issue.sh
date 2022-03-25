#!/bin/bash
set -x

shopt -s expand_aliases

# ASSUMES elementsd IS ALREADY RUNNING

######################################################
#                                                    #
#    SCRIPT CONFIG - PLEASE REVIEW BEFORE RUNNING    #
#                                                    #
######################################################

# Amend the following:
# 5-255 ASCII chars
NAME="Embit test asset"
# 3-24 chars a-zA-Z0-9.-
TICKER="EMTST"
# Do not use a domain prefix in the following:
DOMAIN="embit.tech"
# Issue 100 assets using the satoshi unit, dependant on PRECISION when viewed from
# applications using Asset Registry data.
ASSET_AMOUNT=0.00012300
# Issue 1 reissuance token using the satoshi unit, unaffected by PRECISION.
TOKEN_AMOUNT=0.00000001

# Amend the following if needed:
PRECISION=2

# Optional collection parameter. Set to "" to ignore:
# COLLECTION="Your-top-level-collection/Your-sub-collection"
COLLECTION=""

# Don't change the following:
VERSION=0

# Change the following to point to your elements-cli binary and liquid live data directory (default is .elements).
# alias e1-cli="elements-cli -datadir=$HOME/.elements"
alias e1-cli="elements-cli --chain=elreg -rpcwallet="

##############################
#                            #
#    END OF SCRIPT CONFIG    #
#                            #
##############################

# Exit on error
set -o errexit

# We will be using the issueasset command and the contract_hash argument:
# issueasset <assetamount> <tokenamount> <blind> <contract_hash>

# As we need to sign the deletion request message later we need
# a legacy address. If you prefer to generate a pubkey and sign
# outside of Elements you can use a regular address instead.
# NEWADDR=$(e1-cli getnewaddress "" legacy)
NEWADDR=$(e1-cli getnewaddress)

VALIDATEADDR=$(e1-cli getaddressinfo $NEWADDR)

PUBKEY=$(echo $VALIDATEADDR | jq -r '.pubkey')

ASSET_ADDR=$NEWADDR

# NEWADDR=$(e1-cli getnewaddress "" legacy)
NEWADDR=$(e1-cli getnewaddress)

TOKEN_ADDR=$NEWADDR

# Create the contract and calculate the contract hash
# The contract is formatted for use in the Blockstream Asset Registry:
if [ "$COLLECTION" = "" ]; then
    CONTRACT='{"entity":{"domain":"'$DOMAIN'"},"issuer_pubkey":"'$PUBKEY'","name":"'$NAME'","precision":'$PRECISION',"ticker":"'$TICKER'","version":'$VERSION'}'
else
    CONTRACT='{"collection":"'$COLLECTION'","entity":{"domain":"'$DOMAIN'"},"issuer_pubkey":"'$PUBKEY'","name":"'$NAME'","precision":'$PRECISION',"ticker":"'$TICKER'","version":'$VERSION'}'
fi

# We will hash using openssl, other options are available
CONTRACT_HASH=$(echo -n $CONTRACT | openssl dgst -sha256)
CONTRACT_HASH=$(echo ${CONTRACT_HASH#"(stdin)= "})

# Reverse the hash
TEMP=$CONTRACT_HASH
LEN=${#TEMP}
until [ $LEN -eq "0" ]; do
    END=${TEMP:(-2)}
    CONTRACT_HASH_REV="$CONTRACT_HASH_REV$END"
    TEMP=${TEMP::-2}
    LEN=$((LEN-2))
done

echo "Contract $CONTRACT"
echo "Contract hash $CONTRACT_HASH"
echo "Contract hash rev $CONTRACT_HASH_REV"

# # Issue the asset and pass in the contract hash
# IA=$(e1-cli issueasset $ASSET_AMOUNT $TOKEN_AMOUNT false $CONTRACT_HASH_REV)

# # Details of the issuance...
# ASSET=$(echo $IA | jq -r '.asset')
# TOKEN=$(echo $IA | jq -r '.token')
# ISSUETX=$(echo $IA | jq -r '.txid')

# #####################################
# #                                   #
# #    ASSET REGISTRY FILE OUTPUTS    #
# #                                   #
# #####################################

# # Output the proof file - you need to place this on your domain.
# echo "Authorize linking the domain name $DOMAIN to the Liquid asset $ASSET" > liquid-asset-proof-$ASSET

# # Create the bash script to run after you have placed the proof file on your domain
# # that will call the registry and request the asset is registered.
# echo "curl https://assets.blockstream.info/ --data-raw '{\"asset_id\":\"$ASSET\",\"contract\":$CONTRACT}'" > register_asset_$ASSET.sh

# # Create the bash script to delete the asset from the registry (if needed later)
# PRIV=$(e1-cli dumpprivkey $ASSET_ADDR)
# SIGNED=$(e1-cli signmessagewithprivkey $PRIV "remove $ASSET from registry")
# echo "curl -X DELETE https://assets.blockstream.info/$ASSET -H 'Content-Type: application/json' -d '{\"signature\":\"$SIGNED\"}'" > delete_asset_$ASSET.sh

# echo "Completed without error"
