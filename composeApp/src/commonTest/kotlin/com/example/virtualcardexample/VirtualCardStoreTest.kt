package com.example.virtualcardexample

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import kotlinx.coroutines.delay // Import delay
import kotlin.test.AfterTest
import kotlin.test.BeforeTest
import kotlin.test.Test
import kotlin.test.assertEquals

@OptIn(ExperimentalCoroutinesApi::class)
class VirtualCardStoreTest {

    private val testDispatcher = StandardTestDispatcher()

    // Mock CardDetailsService for testing
    class MockCardDetailsService : CardDetailsService() {
        override suspend fun fetchCardDetails(): CardDetails {
            delay(100) // Simulate a network delay
            return CardDetails(
                cardNumber = "1111 2222 3333 4444",
                cardHolder = "Test User",
                expiry = "11/22",
                cvv = "789"
            )
        }
    }

    @BeforeTest
    fun setup() {
        Dispatchers.setMain(testDispatcher)
    }

    @AfterTest
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun testInitialState() = runTest {
        val store = VirtualCardStore(MockCardDetailsService())
        // The init block dispatches LoadCardDetails, which launches a coroutine.
        // We need to run the dispatcher to allow the coroutine to start and set isLoading to true.
        testDispatcher.scheduler.runCurrent()

        assertEquals(true, store.state.value.isLoading)
        assertEquals(false, store.state.value.isRevealed)
        assertEquals(false, store.state.value.isLocked)

        // Advance past the initial loadCardDetails call in the init block (which includes the suspending fetch)
        advanceUntilIdle()
        val state = store.state.value
        
        assertEquals("**** **** **** 4444", state.cardNumber)
        assertEquals("Test User", state.cardHolder)
        assertEquals("**/**", state.expiry)
        assertEquals("***", state.cvv)
        assertEquals("Reveal Details", state.buttonText)
        assertEquals(false, state.isRevealed)
        assertEquals(false, state.isLoading)
        assertEquals(false, state.isLocked)
    }

    @Test
    fun testToggleVisibility() = runTest {
        val store = VirtualCardStore(MockCardDetailsService())
        advanceUntilIdle() // Complete initial loading

        // Initial check after loading is complete
        assertEquals(false, store.state.value.isRevealed)
        assertEquals(false, store.state.value.isLoading)
        assertEquals(false, store.state.value.isLocked)

        // Toggle ON
        store.dispatch(VirtualCardIntent.ToggleVisibility)
        
        val revealedState = store.state.value
        assertEquals(true, revealedState.isRevealed)
        assertEquals("1111 2222 3333 4444", revealedState.cardNumber)
        assertEquals("11/22", revealedState.expiry)
        assertEquals("789", revealedState.cvv)
        assertEquals("Hide Details", revealedState.buttonText)
        assertEquals(false, revealedState.isLoading)
        assertEquals(false, revealedState.isLocked)

        // Toggle OFF
        store.dispatch(VirtualCardIntent.ToggleVisibility)
        
        val hiddenState = store.state.value
        assertEquals(false, hiddenState.isRevealed)
        assertEquals("**** **** **** 4444", hiddenState.cardNumber)
        assertEquals("Reveal Details", hiddenState.buttonText)
        assertEquals(false, hiddenState.isLoading)
        assertEquals(false, hiddenState.isLocked)
    }

    @Test
    fun testLoadCardDetails() = runTest {
        val store = VirtualCardStore(MockCardDetailsService())
        advanceUntilIdle() // Complete initial loading

        // Simulate a revealed state before loading new details
        store.dispatch(VirtualCardIntent.ToggleVisibility)
        assertEquals(true, store.state.value.isRevealed)
        assertEquals(false, store.state.value.isLoading)
        assertEquals(false, store.state.value.isLocked)

        // Dispatch LoadCardDetails intent
        store.dispatch(VirtualCardIntent.LoadCardDetails)

        // Should be loading immediately after dispatch
        testDispatcher.scheduler.runCurrent() // Allow coroutine to start and update isLoading
        assertEquals(true, store.state.value.isLoading)
        assertEquals(false, store.state.value.isRevealed) // Should reset reveal state
        assertEquals("Reveal Details", store.state.value.buttonText)
        assertEquals(false, store.state.value.isLocked) // Should reset locked state

        // Advance past the delay
        advanceUntilIdle()

        // Should no longer be loading and details should be reset
        assertEquals(false, store.state.value.isLoading)
        assertEquals(false, store.state.value.isRevealed)
        assertEquals("**** **** **** 4444", store.state.value.cardNumber)
        assertEquals("Test User", store.state.value.cardHolder)
        assertEquals("**/**", store.state.value.expiry)
        assertEquals("***", store.state.value.cvv)
        assertEquals("Reveal Details", store.state.value.buttonText)
        assertEquals(false, store.state.value.isLocked)
    }

    @Test
    fun testLoadingStateDuringLoadCardDetails() = runTest {
        val store = VirtualCardStore(MockCardDetailsService())

        // After store creation, init block dispatches LoadCardDetails, which launches a coroutine.
        // We need to run the dispatcher to allow the coroutine to start and set isLoading to true.
        testDispatcher.scheduler.runCurrent()
        assertEquals(true, store.state.value.isLoading) 
        assertEquals(false, store.state.value.isRevealed)
        assertEquals("Reveal Details", store.state.value.buttonText)
        assertEquals(false, store.state.value.isLocked)
        
        advanceUntilIdle() // complete the initial loading

        assertEquals(false, store.state.value.isLoading) // Should be false after initial load

        // Dispatch LoadCardDetails again
        store.dispatch(VirtualCardIntent.LoadCardDetails)

        // Should be loading immediately after dispatch
        testDispatcher.scheduler.runCurrent() // Allow coroutine to start and update isLoading
        assertEquals(true, store.state.value.isLoading)
        assertEquals(false, store.state.value.isRevealed) // Should also reset revealed state
        assertEquals(false, store.state.value.isLocked) // Should also reset locked state

        // Advance until idle to complete the loading
        advanceUntilIdle()

        // Should no longer be loading
        assertEquals(false, store.state.value.isLoading)
    }

    @Test
    fun testToggleLock_lockCard() = runTest {
        val store = VirtualCardStore(MockCardDetailsService())
        advanceUntilIdle() // Complete initial loading

        // Lock the card
        store.dispatch(VirtualCardIntent.ToggleLock)
        val lockedState = store.state.value
        assertEquals(true, lockedState.isLocked)
        assertEquals(false, lockedState.isRevealed)
        assertEquals("**** **** **** 4444", lockedState.cardNumber)
        assertEquals("Reveal Details", lockedState.buttonText)
    }

    @Test
    fun testToggleLock_unlockCard() = runTest {
        val store = VirtualCardStore(MockCardDetailsService())
        advanceUntilIdle() // Complete initial loading

        // Lock the card first
        store.dispatch(VirtualCardIntent.ToggleLock)
        assertEquals(true, store.state.value.isLocked)

        // Unlock the card
        store.dispatch(VirtualCardIntent.ToggleLock)
        val unlockedState = store.state.value
        assertEquals(false, unlockedState.isLocked)
        assertEquals(false, unlockedState.isRevealed) // Should remain hidden after unlock
        assertEquals("Reveal Details", unlockedState.buttonText)
    }

    @Test
    fun testToggleLock_thenToggleVisibility() = runTest {
        val store = VirtualCardStore(MockCardDetailsService())
        advanceUntilIdle() // Complete initial loading

        // Lock the card
        store.dispatch(VirtualCardIntent.ToggleLock)
        assertEquals(true, store.state.value.isLocked)

        // Try to reveal details (should not work while locked)
        store.dispatch(VirtualCardIntent.ToggleVisibility)
        val stateAfterLockedVisibilityAttempt = store.state.value
        assertEquals(true, stateAfterLockedVisibilityAttempt.isLocked)
        assertEquals(false, stateAfterLockedVisibilityAttempt.isRevealed)
        assertEquals("Reveal Details", stateAfterLockedVisibilityAttempt.buttonText)

        // Unlock the card
        store.dispatch(VirtualCardIntent.ToggleLock)
        assertEquals(false, store.state.value.isLocked)

        // Now reveal details (should work)
        store.dispatch(VirtualCardIntent.ToggleVisibility)
        val stateAfterUnlockedVisibility = store.state.value
        assertEquals(false, stateAfterUnlockedVisibility.isLocked)
        assertEquals(true, stateAfterUnlockedVisibility.isRevealed)
        assertEquals("Hide Details", stateAfterUnlockedVisibility.buttonText)
        assertEquals("1111 2222 3333 4444", stateAfterUnlockedVisibility.cardNumber)
    }
}