package com.example.virtualcardexample

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeContentPadding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import org.jetbrains.compose.ui.tooling.preview.Preview
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.graphics.Brush
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics

@Composable
@Preview
fun App() {
    MaterialTheme {
        VirtualCardScreen()
    }
}

@Composable
fun VirtualCardScreen() {
    val store = androidx.lifecycle.viewmodel.compose.viewModel { VirtualCardStore() }
    val state by store.state.collectAsState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .safeContentPadding(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        VirtualCard(
            cardNumber = state.cardNumber,
            cardHolder = state.cardHolder,
            expiry = state.expiry,
            cvv = state.cvv,
            isLoading = state.isLoading,
            isLocked = state.isLocked
        )
        
        Spacer(modifier = Modifier.height(32.dp))
        
        Button(
            onClick = { store.dispatch(VirtualCardIntent.ToggleVisibility) },
            modifier = Modifier.testTag("RevealButton"),
            enabled = !state.isLocked && !state.isLoading
        ) {
            Text(state.buttonText)
        }

        Spacer(modifier = Modifier.height(16.dp))

        Button(
            onClick = { store.dispatch(VirtualCardIntent.ToggleLock) },
            modifier = Modifier.testTag("LockCardButton"),
            enabled = !state.isLoading
        ) {
            Text(if (state.isLocked) "Unlock Card" else "Lock Card")
        }
    }
}

@Composable
fun VirtualCard(
    cardNumber: String,
    cardHolder: String,
    expiry: String,
    cvv: String,
    isLoading: Boolean,
    isLocked: Boolean
) {
    Card(
        modifier = Modifier
            .fillMaxWidth(0.9f)
            .height(220.dp)
            .testTag("CreditCard"),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primaryContainer
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 8.dp)
    ) {
        Box(modifier = Modifier.fillMaxSize()) {
            // Background Gradient or Design
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(
                        brush = Brush.linearGradient(
                            colors = listOf(
                                MaterialTheme.colorScheme.primary,
                                MaterialTheme.colorScheme.tertiary
                            )
                        )
                    )
            )

            if (isLoading) {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator(color = Color.White, modifier = Modifier.semantics { contentDescription = "Loading" })
                }
            } else if (isLocked) {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "CARD LOCKED",
                        style = MaterialTheme.typography.headlineSmall,
                        color = Color.White,
                        fontWeight = FontWeight.Bold
                    )
                }
            } else {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(24.dp),
                    verticalArrangement = Arrangement.SpaceBetween
                ) {
                    // Bank Name / Logo Placeholder
                    Text(
                        text = "NeoBank",
                        style = MaterialTheme.typography.titleLarge,
                        color = Color.White,
                        fontWeight = FontWeight.Bold
                    )

                    // Chip
                    Box(
                        modifier = Modifier
                            .width(50.dp)
                            .height(35.dp)
                            .background(
                                color = Color(0xFFE0E0E0),
                                shape = RoundedCornerShape(4.dp)
                            )
                    )

                    // Card Details
                    Column {
                        Text(
                            text = cardNumber,
                            style = MaterialTheme.typography.headlineMedium,
                            color = Color.White,
                            fontFamily = FontFamily.Monospace,
                            modifier = Modifier.testTag("CardNumber")
                        )
                        
                        Spacer(modifier = Modifier.height(16.dp))
                        
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Column {
                                Text(
                                    text = "CARD HOLDER",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = Color.White.copy(alpha = 0.8f)
                                )
                                Text(
                                    text = cardHolder,
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = Color.White
                                )
                            }
                            
                            Column {
                                Text(
                                    text = "EXPIRES",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = Color.White.copy(alpha = 0.8f)
                                )
                                Text(
                                    text = expiry,
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = Color.White
                                )
                            }
                            
                             Column {
                                Text(
                                    text = "CVV",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = Color.White.copy(alpha = 0.8f)
                                )
                                Text(
                                    text = cvv,
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = Color.White
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}
