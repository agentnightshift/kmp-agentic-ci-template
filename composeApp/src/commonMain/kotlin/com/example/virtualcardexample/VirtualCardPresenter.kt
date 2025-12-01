package com.example.virtualcardexample

class VirtualCardPresenter {
    fun getCardNumber(isRevealed: Boolean): String {
        return if (isRevealed) "1234 5678 9012 3456" else "**** **** **** 3456"
    }

    fun getExpiry(isRevealed: Boolean): String {
        return if (isRevealed) "12/28" else "**/**"
    }

    fun getCvv(isRevealed: Boolean): String {
        return if (isRevealed) "123" else "***"
    }
    
    fun getButtonText(isRevealed: Boolean): String {
        return if (isRevealed) "Hide Details" else "Reveal Details"
    }
}
