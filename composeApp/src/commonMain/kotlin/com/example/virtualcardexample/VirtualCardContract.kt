package com.example.virtualcardexample

data class VirtualCardState(
    val cardNumber: String = "**** **** **** 3456",
    val cardHolder: String = "Nick Antigravity",
    val expiry: String = "**/**",
    val cvv: String = "***",
    val isRevealed: Boolean = false,
    val isLocked: Boolean = false,
    val buttonText: String = "Reveal Details",
    val isLoading: Boolean = false
)

sealed interface VirtualCardIntent {
    data object ToggleVisibility : VirtualCardIntent
    data object ToggleLock : VirtualCardIntent
    data object LoadCardDetails : VirtualCardIntent
}

// Data class to represent the fetched card details
data class CardDetails(
    val cardNumber: String,
    val cardHolder: String,
    val expiry: String,
    val cvv: String
)
