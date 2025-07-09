# Land Mapping App

A Flutter application to map land boundaries, manage land records, and visualize mapped areas on Google Maps. The app allows users to add, view, and delete land boundaries, and provides a simple workflow for field data collection and management. Further this will be used by backend service to download geo satellite data to create analytics.

## Features

- Add new land boundaries by marking points on a map.
- View a list of all mapped lands with area, unit, and status (e.g., Processed, Submitted).
- View land details and boundaries on the map.
- Swipe to delete lands (Gmail-like swipe-to-delete).
- First-time usage instructions for new users.
- Data persistence and retrieval via backend API.

## Setup Instructions

### Prerequisites

- Flutter SDK installed on your system.
- Android Studio or VS Code for development.
- A Google Maps API Key (see below).

### 1. Clone the Repository

Clone this repository to your local machine.  
**Location:** Any folder of your choice.

```sh
git clone <your-repository-url>
cd land_mapping
```

### 2. Install Dependencies

Run the following command in the project root folder (`land_mapping/`):

```sh
flutter pub get
```

### 3. Get a Google Maps API Key

- Go to the Google Cloud Console.
- Create a new project (or select an existing one).
- Enable the **Maps SDK for Android** and **Geocoding API**.
- Create an API key.

### 4. Add Your API Key

- Open the file: `android/key.properties` in your project.
- Add your API key as follows (replace with your actual key):

  ```
  MAPS_API_KEY=YOUR_GOOGLE_MAPS_API_KEY
  ```

### 5. Run the App

From the project root folder, run:

```sh
flutter run
```

You can run the app on an emulator or a physical device.

## Workflow

1. **Add Land**: Tap the "+" button to start mapping a new land. Mark points on the map to define the boundary (long press on the map or use the mark button for your current location).
2. **Save Land**: After marking all points, save the land by providing a name and (optionally) your email.
3. **View Lands**: The main screen lists all your mapped lands with area, unit, and status.
4. **View Details**: Tap a land to view its boundary on the map.
5. **Delete Land**: Swipe left on a land in the list to delete it (Gmail-style swipe-to-delete).
6. **Refresh**: Pull down to refresh the land list.

## Notes

- The app requires location permissions to function.
- Make sure your device/emulator has Google Play Services and internet connectivity.
- For any issues, check the Flutter documentation.

### 6. Install on Android Device

To install the app on a physical Android device:

1. **Build the APK:**

   From the project root folder, run:
   ```sh
   flutter build apk --release
   ```
   The APK will be generated at `build/app/outputs/flutter-apk/app-release.apk`.

2. **Transfer the APK to your device:**

   You can use USB, Bluetooth, email, or any file-sharing app to move the APK to your Android device.

3. **Allow installation from unknown sources:**

   - On your Android device, go to **Settings > Security** (or **Settings > Apps & notifications > Special app access > Install unknown apps** on newer Android versions).
   - Find your file manager or browser app and enable **Allow from this source**.

4. **Install the APK:**

   - Open the APK file on your device using a file manager.
   - Tap **Install** and follow the prompts.

5. **Open the App:**

   - Once installed, you can open the app from your app drawer.

---

**Note:**  
You may need to grant location permissions and ensure Google Play Services are available on your device for the app to function correctly.

## Folder Structure (`lib/`)

## Folder Structure

The project is organized as follows:

```
land_mapping/
├── android/         # Android native code and config (add MAPS_API_KEY in key.properties)
├── assets/          # App assets (images, icons, etc.)
├── build/           # Generated build files (auto-created)
├── ios/             # iOS native code and config
├── lib/             # Main Dart source code
│   ├── config/      # App configuration files
│   ├── models/      # Data models (e.g., LandResponse)
│   ├── screens/     # UI screens (Landing, Map, Home, etc.)
│   ├── services/    # API, device info, and permission services
│   ├── widgets/     # Reusable widgets (dialogs, custom UI components)
│   └── main.dart    # App entry point
├── pubspec.yaml     # Flutter/Dart dependencies and project metadata
├── README.md        # Project documentation
└── ...              # Other config and metadata files
```

## API Endpoints

Below are the main API endpoints used by the app.  
The base API URL is configured in [`lib/config/app_config.dart`](lib/config/app_config.dart).  
**Example base URL:** `http://localhost:3000/api/v1`

| Endpoint Description                | HTTP Method | Example URL                                      | Notes                                 |
|-------------------------------------|-------------|--------------------------------------------------|---------------------------------------|
| Save Land Boundary                  | POST        | `http://localhost:3000/api/v1/lands`             | Body: `{ land_name, coordinates, user_id, user_email }` |
| Get Lands by User ID                | GET         | `http://localhost:3000/api/v1/lands/user/{userId}` | Replace `{userId}` with actual user id |
| Delete Land                         | DELETE      | `http://localhost:3000/api/v1/lands/{landId}`    | Replace `{landId}` with actual land id |
| Generate Vegetation Report for Land | POST        | `http://localhost:3000/api/v1/reports/vegetation/{landId}` | Replace `{landId}` with actual land id |

You can update the API base URL in [`lib/config/app_config.dart`](lib/config/app_config.dart) as needed for your environment.

---

---

Happy Mapping!