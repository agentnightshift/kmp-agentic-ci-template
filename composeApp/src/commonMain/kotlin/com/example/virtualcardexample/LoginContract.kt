package com.example.virtualcardexample

/**
 * State for the Login screen.
 * This is a basic non-functional login screen for demonstration purposes.
 */
data class LoginState(
    val email: String = "",
    val password: String = "",
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
    val isPasswordVisible: Boolean = false
)

/**
 * Intent (user actions) for the Login screen.
 */
sealed interface LoginIntent {
    data class EmailChanged(val email: String) : LoginIntent
    data class PasswordChanged(val password: String) : LoginIntent
    data object TogglePasswordVisibility : LoginIntent
    data object LoginClicked : LoginIntent
    data object ForgotPasswordClicked : LoginIntent
    data object SignUpClicked : LoginIntent
}
