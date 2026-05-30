package com.watchfy.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

@Composable
fun ShimmerBox(
    modifier: Modifier = Modifier,
    borderRadius: Float = 12f
) {
    Box(
        modifier = modifier
            .background(Color(0xFF27272A), shape = RoundedCornerShape(borderRadius.dp))
    )
}