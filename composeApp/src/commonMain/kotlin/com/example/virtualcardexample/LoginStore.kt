package com.example.virtualcardexample

import androidx.lifecycle.ViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

/**
 * Store (ViewModel) for the Login screen.
 * Processes intents and updates state following MVI pattern.
 *
 * Note: This is a non-functional demo - login does not actually authenticate.
 */
class LoginStore : ViewModel() {

    private val _state = MutableStateFlow(LoginState())
    val state: StateFlow<LoginState> = _state.asStateFlow()

    fun dispatch(intent: LoginIntent) {
        when (intent) {
            is LoginIntent.EmailChanged -> {
                _state.update { it.copy(email = intent.email, errorMessage = null) }
            }
            is LoginIntent.PasswordChanged -> {
                _state.update { it.copy(password = intent.password, errorMessage = null) }
            }
            is LoginIntent.TogglePasswordVisibility -> {
                _state.update { it.copy(isPasswordVisible = !it.isPasswordVisible) }
            }
            is LoginIntent.LoginClicked -> {
                handleLogin()
            }
            is LoginIntent.ForgotPasswordClicked -> {
                // Non-functional - would navigate to forgot password screen
                _state.update { it.copy(errorMessage = "Forgot password not implemented") }
            }
            is LoginIntent.SignUpClicked -> {
                // Non-functional - would navigate to sign up screen
                _state.update { it.copy(errorMessage = "Sign up not implemented") }
            }
        }
    }

    private fun handleLogin() {
        val currentState = _state.value

        // Basic validation
        if (currentState.email.isBlank()) {
            _state.update { it.copy(errorMessage = "Email is required") }
            return
        }

        if (currentState.password.isBlank()) {
            _state.update { it.copy(errorMessage = "Password is required") }
            return
        }

        // Non-functional demo - just show a message
        // In a real app, this would make an API call
        _state.update {
            it.copy(
                isLoading = false,
                errorMessage = "Login is not implemented (demo screen)"
            )
        }
    }
}
