# Keep Retrofit interfaces
-keep,allowobfuscation interface * {
    @retrofit2.http.* <methods>;
}
-dontwarn retrofit2.**
-keep class retrofit2.** { *; }

# Keep Gson serialized classes
-keepclassmembers class com.watchfy.app.data.remote.dto.** { *; }
-keepclassmembers class com.watchfy.app.domain.model.** { *; }

# Keep Room entities
-keepclassmembers class com.watchfy.app.data.local.entity.** { *; }

# Keep Hilt
-keepclassmembers class * {
    @dagger.hilt.android.EarlyEntryPoint <fields>;
}
