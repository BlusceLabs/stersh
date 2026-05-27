package com.watchfy.app.ui.player

import android.net.Uri
import androidx.compose.foundation.layout.*
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.media3.common.MediaItem
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.exoplayer.hls.HlsMediaSource
import androidx.media3.ui.AspectRatioFrameLayout
import androidx.media3.ui.PlayerView

@Composable
fun ExoPlayerView(
    hlsUrl: String,
    modifier: Modifier = Modifier,
    startTime: Long = 0,
    onProgress: (Long, Long) -> Unit = { _, _ -> },
    onNext: (() -> Unit)? = null,
    onPrev: (() -> Unit)? = null,
) {
    var player by remember { mutableStateOf<ExoPlayer?>(null) }
    val context = LocalContext.current

    LaunchedEffect(Unit) {
        player?.seekTo(startTime)
    }

    DisposableEffect(hlsUrl) {
        val exoPlayer = ExoPlayer.Builder(context)
            .build()
            .apply {
                val uri = Uri.parse(hlsUrl)
                val mediaSource = HlsMediaSource.Factory(
                    androidx.media3.datasource.DefaultHttpDataSource.Factory()
                        .setAllowCrossProtocolRedirects(true)
                        .setConnectTimeoutMs(30_000)
                        .setReadTimeoutMs(120_000)
                ).createMediaSource(MediaItem.fromUri(uri))

                setMediaSource(mediaSource)
                prepare()
                playWhenReady = true
                if (startTime > 0) seekTo(startTime)

                addListener(object : Player.Listener {
                    override fun onPlaybackStateChanged(playbackState: Int) {
                        if (playbackState == Player.STATE_READY && startTime > 0) {
                            seekTo(startTime)
                        }
                    }

                    override fun onPlayerError(error: PlaybackException) {
                    }
                })
            }

        player = exoPlayer

        onDispose {
            exoPlayer.release()
            player = null
        }
    }

    LaunchedEffect(player) {
        if (player == null) return@LaunchedEffect
        while (true) {
            kotlinx.coroutines.delay(15_000)
            val p = player ?: break
            if (p.duration > 0) {
                onProgress(p.currentPosition, p.duration)
            }
        }
    }

    AndroidView(
        modifier = modifier.aspectRatio(16f / 9f),
        factory = {
            PlayerView(context).apply {
                player = player
                useController = true
                setShowNextButton(onNext != null)
                setShowPreviousButton(onPrev != null)
                setKeepContentOnPlayerReset(true)
                resizeMode = AspectRatioFrameLayout.RESIZE_MODE_FIT
            }
        },
        update = { view ->
            view.player = player
        }
    )
}
