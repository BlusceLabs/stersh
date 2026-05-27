package com.watchfy.app.ui.screens.details

import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.watchfy.app.domain.model.*
import coil.compose.AsyncImage

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DetailsScreen(
    mediaType: String,
    tmdbId: Int,
    onPlay: (Int, Int) -> Unit,
    onNavigateToDetails: (Int) -> Unit,
    onBack: () -> Unit,
    viewModel: DetailsViewModel = hiltViewModel()
) {
    LaunchedEffect(mediaType, tmdbId) { viewModel.load(mediaType, tmdbId) }
    val state by viewModel.state.collectAsState()

    when {
        state.loading -> Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
        }
        state.error != null -> Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text(state.error ?: "Error", color = MaterialTheme.colorScheme.error)
        }
        else -> {
            val title = state.movie?.title ?: state.tvShow?.name ?: ""
            val backdrop = state.movie?.backdropPath ?: state.tvShow?.backdropPath
            val poster = state.movie?.posterPath ?: state.tvShow?.posterPath
            val overview = state.movie?.overview ?: state.tvShow?.overview ?: ""
            val rating = state.movie?.voteAverage ?: state.tvShow?.voteAverage ?: 0.0
            val genres = state.movie?.genres ?: state.tvShow?.genres ?: emptyList()
            val year = (state.movie?.releaseDate ?: state.tvShow?.firstAirDate ?: "").take(4)

            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState())
            ) {
                // Backdrop
                Box(modifier = Modifier.fillMaxWidth().height(280.dp)) {
                    AsyncImage(
                        model = "https://image.tmdb.org/t/p/original$backdrop",
                        contentDescription = null,
                        contentScale = ContentScale.Crop,
                        modifier = Modifier.fillMaxSize()
                    )
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .background(Brush.verticalGradient(listOf(Color.Transparent, Color(0xFF09090B))))
                    )
                    IconButton(onClick = onBack, modifier = Modifier.align(Alignment.TopStart).padding(8.dp)) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back", tint = Color.White)
                    }
                }

                Column(modifier = Modifier.fillMaxWidth().padding(16.dp)) {
                    // Title
                    Text(title, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, color = Color.White)

                    Spacer(modifier = Modifier.height(8.dp))

                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("★ ${"%.1f".format(rating)}", color = Color(0xFFEF4444), fontWeight = FontWeight.Bold)
                        if (year.isNotEmpty()) Text(" • $year", color = Color.Gray)
                        Spacer(modifier = Modifier.width(8.dp))
                        genres.take(3).forEach { genre ->
                            Text(genre.name, color = Color.Gray, fontSize = 12.sp)
                            if (genre != genres.take(3).last()) Text(" • ", color = Color.Gray)
                        }
                    }

                    Spacer(modifier = Modifier.height(16.dp))

// Play button
                     Button(
                         onClick = { onPlay(1, 1) },
                         colors = ButtonDefaults.buttonColors(containerColor = Color.White, contentColor = Color.Black),
                         modifier = Modifier.fillMaxWidth().height(48.dp),
                         shape = RoundedCornerShape(12.dp)
                     ) {
                         Icon(Icons.Default.PlayArrow, null, modifier = Modifier.size(20.dp))
                         Spacer(modifier = Modifier.width(8.dp))
                         Text("Play", fontWeight = FontWeight.Bold)
                     }

                     // Trailer button
                     if (state.trailerKey != null) {
                         Spacer(modifier = Modifier.height(8.dp))
                         OutlinedButton(
                             onClick = { /* open YouTube */ },
                             modifier = Modifier.fillMaxWidth().height(44.dp),
                             shape = RoundedCornerShape(12.dp),
                             colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White)
                         ) {
                             Text("▶ Trailer", fontWeight = FontWeight.SemiBold)
                         }
                     }

                    Spacer(modifier = Modifier.height(8.dp))

                    // My List button
                    OutlinedButton(
                        onClick = { viewModel.toggleMyList(mediaType, tmdbId) },
                        modifier = Modifier.fillMaxWidth().height(44.dp),
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White)
                    ) {
                        if (state.isInMyList) {
                            Icon(Icons.Default.Check, null, modifier = Modifier.size(18.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                        }
                        Text(if (state.isInMyList) "In Your List" else "Add to My List", fontWeight = FontWeight.SemiBold)
                    }

                    Spacer(modifier = Modifier.height(16.dp))

                    // Seasons (TV only)
                    if (mediaType == "tv" && state.seasons.isNotEmpty()) {
                        Text("Seasons", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = Color.White)
                        Spacer(modifier = Modifier.height(8.dp))
                        state.seasons.forEach { season ->
                            Surface(
                                onClick = { onPlay(season.seasonNumber, 1) },
                                modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                                shape = RoundedCornerShape(12.dp),
                                color = MaterialTheme.colorScheme.surfaceVariant
                            ) {
                                Row(modifier = Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                                    Column(modifier = Modifier.weight(1f)) {
                                        Text(season.name, fontWeight = FontWeight.SemiBold, color = Color.White)
                                        Text("${season.episodeCount} episodes", color = Color.Gray, fontSize = 12.sp)
                                    }
                                    Icon(Icons.Default.PlayArrow, null, tint = Color.White)
                                }
                            }
                        }
                        Spacer(modifier = Modifier.height(16.dp))
                    }

                    // Overview
                    Text("Overview", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = Color.White)
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(overview, color = Color.LightGray, lineHeight = 22.sp)

                    // Recommendations
                    if (state.recommendations.isNotEmpty()) {
                        Spacer(modifier = Modifier.height(20.dp))
                        Text("Recommendations", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = Color.White)
                        Spacer(modifier = Modifier.height(8.dp))
                        LazyRow(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
items(state.recommendations) { rec ->
                             Column(
                                 modifier = Modifier.width(120.dp).clickable { onNavigateToDetails(rec.id) }
                             ) {
                                    AsyncImage(
                                        model = "https://image.tmdb.org/t/p/w342${rec.posterPath}",
                                        contentDescription = null,
                                        contentScale = ContentScale.Crop,
                                        modifier = Modifier.width(120.dp).height(180.dp).clip(RoundedCornerShape(8.dp)).background(MaterialTheme.colorScheme.surfaceVariant)
                                    )
                                    Spacer(modifier = Modifier.height(4.dp))
                                    Text(rec.title, color = Color.White, fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
