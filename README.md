# nornir-salt
Collection of Nornir plugins used by SALTSTACK Nornir modules (proxy, execution)

## Runners

- **QueueRunner** - simple queue runner
- **RetryRunner** - runner that implements retry logic for connections and tasks

## Inventory

- **DictInventory** - Inventory plugin that accepts dictionary structure to populate hosts' inventory

# Functions

- **ResultSerializer** - helper function to transform AggregatedResult object in Python dictionary