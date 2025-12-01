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
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import org.jetbrains.compose.ui.tooling.preview.Preview

@Composable
@Preview
fun App() {
    MaterialTheme {
        VirtualCardScreen()
    }
}

@Composable
fun VirtualCardScreen() {
    var isRevealed by remember { mutableStateOf(false) }
    val presenter = remember { VirtualCardPresenter() }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .safeContentPadding(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = androidx.compose.foundation.layout.Arrangement.Center
    ) {
        VirtualCard(isRevealed = isRevealed, presenter = presenter)
        
        androidx.compose.foundation.layout.Spacer(modifier = Modifier.height(32.dp))
        
        Button(
            onClick = { isRevealed = !isRevealed },
            modifier = Modifier.testTag("RevealButton")
        ) {
            Text(presenter.getButtonText(isRevealed))
        }
    }
}

@Composable
fun VirtualCard(isRevealed: Boolean, presenter: VirtualCardPresenter) {
    val cardNumber = presenter.getCardNumber(isRevealed)
    val cardHolder = "Nick Antigravity"
    val expiry = presenter.getExpiry(isRevealed)
    val cvv = presenter.getCvv(isRevealed)

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
                        brush = androidx.compose.ui.graphics.Brush.linearGradient(
                            colors = listOf(
                                MaterialTheme.colorScheme.primary,
                                MaterialTheme.colorScheme.tertiary
                            )
                        )
                    )
            )

            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(24.dp),
                verticalArrangement = androidx.compose.foundation.layout.Arrangement.SpaceBetween
            ) {
                // Bank Name / Logo Placeholder
                Text(
                    text = "NeoBank",
                    style = MaterialTheme.typography.titleLarge,
                    color = androidx.compose.ui.graphics.Color.White,
                    fontWeight = androidx.compose.ui.text.font.FontWeight.Bold
                )

                // Chip
                Box(
                    modifier = Modifier
                        .width(50.dp)
                        .height(35.dp)
                        .background(
                            color = androidx.compose.ui.graphics.Color(0xFFE0E0E0),
                            shape = androidx.compose.foundation.shape.RoundedCornerShape(4.dp)
                        )
                )

                // Card Details
                Column {
                    Text(
                        text = cardNumber,
                        style = MaterialTheme.typography.headlineMedium,
                        color = androidx.compose.ui.graphics.Color.White,
                        fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace,
                        modifier = Modifier.testTag("CardNumber")
                    )
                    
                    androidx.compose.foundation.layout.Spacer(modifier = Modifier.height(16.dp))
                    
                    androidx.compose.foundation.layout.Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = androidx.compose.foundation.layout.Arrangement.SpaceBetween
                    ) {
                        Column {
                            Text(
                                text = "CARD HOLDER",
                                style = MaterialTheme.typography.labelSmall,
                                color = androidx.compose.ui.graphics.Color.White.copy(alpha = 0.8f)
                            )
                            Text(
                                text = cardHolder,
                                style = MaterialTheme.typography.bodyMedium,
                                color = androidx.compose.ui.graphics.Color.White
                            )
                        }
                        
                        Column {
                            Text(
                                text = "EXPIRES",
                                style = MaterialTheme.typography.labelSmall,
                                color = androidx.compose.ui.graphics.Color.White.copy(alpha = 0.8f)
                            )
                            Text(
                                text = expiry,
                                style = MaterialTheme.typography.bodyMedium,
                                color = androidx.compose.ui.graphics.Color.White
                            )
                        }
                        
                         Column {
                            Text(
                                text = "CVV",
                                style = MaterialTheme.typography.labelSmall,
                                color = androidx.compose.ui.graphics.Color.White.copy(alpha = 0.8f)
                            )
                            Text(
                                text = cvv,
                                style = MaterialTheme.typography.bodyMedium,
                                color = androidx.compose.ui.graphics.Color.White
                            )
                        }
                    }
                }
            }
        }
    }
}