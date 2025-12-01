package com.example.virtualcardexample

import kotlin.test.Test
import kotlin.test.assertEquals

class VirtualCardPresenterTest {

    private val presenter = VirtualCardPresenter()

    @Test
    fun testCardNumber() {
        assertEquals("**** **** **** 3456", presenter.getCardNumber(false))
        assertEquals("1234 5678 9012 3456", presenter.getCardNumber(true))
    }

    @Test
    fun testExpiry() {
        assertEquals("**/**", presenter.getExpiry(false))
        assertEquals("12/28", presenter.getExpiry(true))
    }

    @Test
    fun testCvv() {
        assertEquals("***", presenter.getCvv(false))
        assertEquals("123", presenter.getCvv(true))
    }

    @Test
    fun testButtonText() {
        assertEquals("Reveal Details", presenter.getButtonText(false))
        assertEquals("Hide Details", presenter.getButtonText(true))
    }
}
