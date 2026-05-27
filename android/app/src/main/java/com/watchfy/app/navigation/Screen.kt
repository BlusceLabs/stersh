package com.watchfy.app.navigation

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Movie
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Tv
import androidx.compose.ui.graphics.vector.ImageVector

sealed class Screen(val route: String, val label: String, val icon: ImageVector? = null) {
    data object Browse : Screen("browse", "Home", Icons.Default.Home)
    data object Movies : Screen("movies", "Movies", Icons.Default.Movie)
    data object TvShows : Screen("tv", "TV Shows", Icons.Default.Tv)
    data object Search : Screen("search", "Search", Icons.Default.Search)

    data object Details : Screen("details/{type}/{id}", "Details") {
        fun createRoute(type: String, id: Int) = "details/$type/$id"
    }

    data object Watch : Screen("watch/{type}/{id}/{season}/{episode}", "Watch") {
        fun createRoute(type: String, id: Int, season: Int = 1, episode: Int = 1) =
            "watch/$type/$id/$season/$episode"
    }

    companion object {
        val bottomNavItems = listOf(Browse, Movies, TvShows, Search)
    }
}
