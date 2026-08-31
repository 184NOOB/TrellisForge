# Hardware and Real-Time Contracts

Replace every placeholder with a verified constraint.

- Protected pins/peripherals/DMA/clock setup: `<HARDWARE_RESOURCES>`
- Flash/EEPROM/NVM layout and erase constraints: `<PERSISTENCE_CONTRACTS>`
- ISR bounded-work rules and forbidden operations: `<ISR_CONTRACTS>`
- Shared state, interrupt masking and concurrency rules: `<CONCURRENCY_CONTRACTS>`
- Protocol/wire compatibility contracts: `<PROTOCOL_CONTRACTS>`
- Board-only validation that AI cannot claim as passed: `<HARDWARE_TESTS>`

