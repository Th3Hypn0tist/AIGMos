# Inputs and Adapters

## Separate categories

Inputs and adapters are not the same thing.

## Inputs

Inputs are system-facing inbound channels.
Example: OSC input.

## Adapters

Adapters are backend / storage / transport integration points.
Examples can include memory, sqlite, or other backends.

## Important architectural rule

Input-originated data lands first in the input model / state flow.
Do not describe an input as the same thing as a storage backend.
