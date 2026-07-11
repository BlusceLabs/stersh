package com.stersh.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val StershColors = darkColorScheme(
    primary = Color(0xFFEF4444),
    onPrimary = Color.White,
    primaryContainer = Color(0xFF7F1D1D),
    secondary = Color(0xFF8B5CF6),
    onSecondary = Color.White,
    surface = Color(0xFF09090B),
    onSurface = Color(0xFFF4F4F5),
    surfaceVariant = Color(0xFF18181B),
    onSurfaceVariant = Color(0xFFA1A1AA),
    background = Color(0xFF09090B),
    onBackground = Color(0xFFF4F4F5),
    outline = Color(0xFF27272A),
    outlineVariant = Color(0xFF3F3F46),
    error = Color(0xFFEF4444),
    scrim = Color(0xFF000000),
)

@Composable
fun StershTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = StershColors,
        typography = androidx.compose.material3.Typography(),
        content = content
    )
}
