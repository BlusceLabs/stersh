package com.watchfy.app.navigation

import androidx.compose.animation.AnimatedContentTransitionScope
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.watchfy.app.ui.components.WatchfyBottomBar
import com.watchfy.app.ui.screens.browse.BrowseScreen
import com.watchfy.app.ui.screens.details.DetailsScreen
import com.watchfy.app.ui.screens.movies.MoviesScreen
import com.watchfy.app.ui.screens.search.SearchScreen
import com.watchfy.app.ui.screens.tv.TvShowsScreen
import com.watchfy.app.ui.screens.watch.WatchScreen

@Composable
fun NavGraph() {
    val navController = rememberNavController()
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentDestination = navBackStackEntry?.destination

    val showBottomBar = Screen.bottomNavItems.any { screen ->
        currentDestination?.hierarchy?.any { it.route == screen.route } == true
    }

    Scaffold(
        bottomBar = {
            if (showBottomBar) {
                WatchfyBottomBar(
                    items = Screen.bottomNavItems,
                    currentDestination = currentDestination,
                    onItemClick = { screen ->
                        navController.navigate(screen.route) {
                            popUpTo(navController.graph.findStartDestination().id) {
                                saveState = true
                            }
                            launchSingleTop = true
                            restoreState = true
                        }
                    }
                )
            }
        }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = Screen.Browse.route,
            modifier = Modifier.padding(innerPadding),
            enterTransition = { fadeIn(animationSpec = tween(300)) },
            exitTransition = { fadeOut(animationSpec = tween(300)) }
        ) {
            composable(Screen.Browse.route) {
                BrowseScreen(
                    onMovieClick = { id -> navController.navigate(Screen.Details.createRoute("movie", id)) },
                    onTvClick = { id -> navController.navigate(Screen.Details.createRoute("tv", id)) }
                )
            }

            composable(Screen.Movies.route) {
                MoviesScreen(
                    onMovieClick = { id -> navController.navigate(Screen.Details.createRoute("movie", id)) }
                )
            }

            composable(Screen.TvShows.route) {
                TvShowsScreen(
                    onTvClick = { id -> navController.navigate(Screen.Details.createRoute("tv", id)) }
                )
            }

            composable(Screen.Search.route) {
                SearchScreen(
                    onMovieClick = { id -> navController.navigate(Screen.Details.createRoute("movie", id)) },
                    onTvClick = { id -> navController.navigate(Screen.Details.createRoute("tv", id)) }
                )
            }

            composable(
                route = Screen.Details.route,
                arguments = listOf(
                    navArgument("type") { type = NavType.StringType },
                    navArgument("id") { type = NavType.IntType }
                )
            ) { backStackEntry ->
                val type = backStackEntry.arguments?.getString("type") ?: "movie"
                val id = backStackEntry.arguments?.getInt("id") ?: 0
                DetailsScreen(
                    mediaType = type,
                    tmdbId = id,
                    onPlay = { season, episode ->
                        navController.navigate(Screen.Watch.createRoute(type, id, season, episode))
                    },
                    onNavigateToDetails = { recId ->
                        navController.navigate(Screen.Details.createRoute(type, recId))
                    },
                    onBack = { navController.popBackStack() }
                )
            }

            composable(
                route = Screen.Watch.route,
                arguments = listOf(
                    navArgument("type") { type = NavType.StringType },
                    navArgument("id") { type = NavType.IntType },
                    navArgument("season") { type = NavType.IntType; defaultValue = 1 },
                    navArgument("episode") { type = NavType.IntType; defaultValue = 1 }
                )
            ) { backStackEntry ->
                val type = backStackEntry.arguments?.getString("type") ?: "movie"
                val id = backStackEntry.arguments?.getInt("id") ?: 0
                val season = backStackEntry.arguments?.getInt("season") ?: 1
                val episode = backStackEntry.arguments?.getInt("episode") ?: 1
                WatchScreen(
                    mediaType = type,
                    tmdbId = id,
                    season = season,
                    episode = episode,
                    onNavigateToEpisode = { s, e ->
                        navController.navigate(Screen.Watch.createRoute(type, id, s, e))
                    },
                    onBack = { navController.popBackStack() }
                )
            }
        }
    }
}
