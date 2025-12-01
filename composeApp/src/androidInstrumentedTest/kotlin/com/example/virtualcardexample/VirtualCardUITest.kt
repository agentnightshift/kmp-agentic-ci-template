package com.example.virtualcardexample

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertTextEquals
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import org.junit.Rule
import org.junit.Test

class VirtualCardUITest {

    @get:Rule
    val composeTestRule = createAndroidComposeRule<MainActivity>()

    @Test
    fun testRevealButtonShowsDetails() {
        // Start the app - MainActivity calls App() automatically
        // composeTestRule.setContent { VirtualCardScreen() } // Not needed if MainActivity sets it, but we can override or just verify what's on screen.
        
        // If we want to test VirtualCardScreen specifically in isolation we could use createComposeRule, 
        // but since we had issues, let's use the Activity rule.
        // MainActivity calls App(), which calls VirtualCardScreen().
        // So we don't need setContent unless we want to override.
        
        // Check initial state (Hidden)
        composeTestRule.onNodeWithTag("RevealButton").assertIsDisplayed()
        composeTestRule.onNodeWithTag("RevealButton").assertTextEquals("Reveal Details")
        
        // Card Number should be masked
        composeTestRule.onNodeWithTag("CardNumber").assertTextEquals("**** **** **** 3456")

        // Click Reveal
        composeTestRule.onNodeWithTag("RevealButton").performClick()

        // Check revealed state
        composeTestRule.onNodeWithTag("RevealButton").assertTextEquals("Hide Details")
        composeTestRule.onNodeWithTag("CardNumber").assertTextEquals("1234 5678 9012 3456")
    }
}
