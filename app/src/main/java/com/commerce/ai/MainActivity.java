package com.commerce.ai;

import android.app.Activity;
import android.os.Bundle;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.graphics.Typeface;
import android.net.Uri;
import android.util.Base64;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

public class MainActivity extends Activity {

    private static final int PICK_IMAGE = 100;

    private static final String API_URL =
            "https://commerce-ai-seven.vercel.app/api/solve";

    private ImageView questionImage;
    private EditText questionInput;
    private TextView result;

    private Uri selectedImageUri = null;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // ==========================================
        // OUTER SCROLLVIEW
        // ==========================================

        ScrollView outerScrollView = new ScrollView(this);
        outerScrollView.setFillViewport(true);

        // ==========================================
        // MAIN LAYOUT
        // ==========================================

        LinearLayout mainLayout = new LinearLayout(this);
        mainLayout.setOrientation(LinearLayout.VERTICAL);
        mainLayout.setPadding(30, 35, 30, 30);
        mainLayout.setBackgroundColor(Color.WHITE);

        // ==========================================
        // TITLE
        // ==========================================

        TextView title = new TextView(this);
        title.setText("Commerce AI");
        title.setTextSize(30);
        title.setTypeface(null, Typeface.BOLD);
        title.setTextColor(Color.BLACK);
        title.setGravity(Gravity.CENTER);

        mainLayout.addView(
                title,
                new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT
                )
        );

        // ==========================================
        // SUBTITLE
        // ==========================================

        TextView subtitle = new TextView(this);
        subtitle.setText("Accountancy & Economics Solver");
        subtitle.setTextSize(16);
        subtitle.setTextColor(Color.DKGRAY);
        subtitle.setGravity(Gravity.CENTER);
        subtitle.setPadding(0, 8, 0, 25);

        mainLayout.addView(subtitle);

        // ==========================================
        // PHOTO BUTTON
        // ==========================================

        Button photoButton = new Button(this);
        photoButton.setText("📷  Upload Question Photo");
        photoButton.setTextSize(16);

        mainLayout.addView(
                photoButton,
                new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT
                )
        );

        // ==========================================
        // QUESTION IMAGE
        // ==========================================

        questionImage = new ImageView(this);
        questionImage.setVisibility(ImageView.GONE);
        questionImage.setAdjustViewBounds(true);
        questionImage.setPadding(10, 15, 10, 15);

        mainLayout.addView(
                questionImage,
                new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        500
                )
        );

        // ==========================================
        // QUESTION INPUT
        // ==========================================

        questionInput = new EditText(this);
        questionInput.setHint("Or type your question here...");
        questionInput.setTextSize(17);
        questionInput.setGravity(Gravity.TOP);
        questionInput.setMinLines(6);
        questionInput.setPadding(20, 20, 20, 20);

        LinearLayout.LayoutParams inputParams =
                new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT
                );

        inputParams.setMargins(0, 15, 0, 20);

        mainLayout.addView(
                questionInput,
                inputParams
        );

        // ==========================================
        // SOLVE BUTTON
        // ==========================================

        Button solveButton = new Button(this);
        solveButton.setText("✨  Solve Question");
        solveButton.setTextSize(17);

        mainLayout.addView(
                solveButton,
                new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT
                )
        );

        // ==========================================
        // ANSWER
        // ==========================================

        result = new TextView(this);

        result.setText(
                "Your complete step-by-step solution will appear here."
        );

        result.setTextSize(16);
        result.setTextColor(Color.DKGRAY);
        result.setPadding(10, 30, 10, 30);
        result.setGravity(Gravity.TOP);
        result.setTextIsSelectable(true);

        mainLayout.addView(
                result,
                new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT
                )
        );

        // ==========================================
        // PUT MAIN LAYOUT INSIDE OUTER SCROLLVIEW
        // ==========================================

        outerScrollView.addView(mainLayout);

        setContentView(outerScrollView);

        // ==========================================
        // PHOTO BUTTON ACTION
        // ==========================================

        photoButton.setOnClickListener(
                view -> openPhotoPicker()
        );

        // ==========================================
        // SOLVE BUTTON ACTION
        // ==========================================

        solveButton.setOnClickListener(
                view -> solveQuestion()
        );
    }

    // ==============================================
    // SOLVE QUESTION
    // ==============================================

    private void solveQuestion() {

        String question =
                questionInput.getText()
                        .toString()
                        .trim();

        if (question.isEmpty()
                && selectedImageUri == null) {

            Toast.makeText(
                    MainActivity.this,
                    "Photo upload karo ya question type karo.",
                    Toast.LENGTH_SHORT
            ).show();

            return;
        }

        result.setText(
                "⏳ AI question solve kar raha hai...\n\n"
                        + "Please wait..."
        );

        new Thread(() -> {

            try {

                String imageData = "";

                if (selectedImageUri != null) {

                    imageData =
                            convertImageToBase64(
                                    selectedImageUri
                            );
                }

                String json =
                        "{"
                                + "\"question\":\""
                                + escapeJson(question)
                                + "\","
                                + "\"image\":\""
                                + escapeJson(imageData)
                                + "\""
                                + "}";

                URL url =
                        new URL(API_URL);

                HttpURLConnection connection =
                        (HttpURLConnection)
                                url.openConnection();

                connection.setRequestMethod("POST");

                connection.setRequestProperty(
                        "Content-Type",
                        "application/json"
                );

                connection.setRequestProperty(
                        "Accept",
                        "application/json"
                );

                connection.setDoOutput(true);

                connection.setConnectTimeout(
                        30000
                );

                connection.setReadTimeout(
                        120000
                );

                OutputStream outputStream =
                        connection.getOutputStream();

                outputStream.write(
                        json.getBytes(
                                StandardCharsets.UTF_8
                        )
                );

                outputStream.flush();
                outputStream.close();

                int responseCode =
                        connection.getResponseCode();

                InputStream inputStream;

                if (responseCode >= 200
                        && responseCode < 300) {

                    inputStream =
                            connection.getInputStream();

                } else {

                    inputStream =
                            connection.getErrorStream();
                }

                String response =
                        readStream(inputStream);

                connection.disconnect();

                String answer =
                        extractJsonValue(
                                response,
                                "answer"
                        );

                String error =
                        extractJsonValue(
                                response,
                                "error"
                        );

                final String finalAnswer =
                        answer;

                final String finalError;

                if (error.isEmpty()) {

                    finalError =
                            "Server error. Response code: "
                                    + responseCode;

                } else {

                    finalError = error;
                }

                runOnUiThread(() -> {

                    if (responseCode >= 200
                            && responseCode < 300
                            && !finalAnswer.isEmpty()) {

                        result.setText(
                                finalAnswer
                        );

                    } else {

                        result.setText(
                                "❌ Error\n\n"
                                        + finalError
                        );
                    }
                });

            } catch (Exception e) {

                final String errorMessage =
                        e.getMessage() != null
                                ? e.getMessage()
                                : "Unknown connection error";

                runOnUiThread(() ->
                        result.setText(
                                "❌ Connection error\n\n"
                                        + errorMessage
                        )
                );
            }

        }).start();
    }

    // ==============================================
    // IMAGE → BASE64
    // ==============================================

    private String convertImageToBase64(
            Uri uri
    ) throws Exception {

        InputStream inputStream =
                getContentResolver()
                        .openInputStream(uri);

        Bitmap bitmap =
                BitmapFactory.decodeStream(
                        inputStream
                );

        inputStream.close();

        if (bitmap == null) {

            throw new Exception(
                    "Image read nahi ho paayi."
            );
        }

        int maxSize = 1600;

        int width = bitmap.getWidth();
        int height = bitmap.getHeight();

        if (width > maxSize
                || height > maxSize) {

            float scale =
                    Math.min(
                            (float) maxSize / width,
                            (float) maxSize / height
                    );

            int newWidth =
                    Math.round(width * scale);

            int newHeight =
                    Math.round(height * scale);

            Bitmap resized =
                    Bitmap.createScaledBitmap(
                            bitmap,
                            newWidth,
                            newHeight,
                            true
                    );

            if (resized != bitmap) {
                bitmap.recycle();
            }

            bitmap = resized;
        }

        ByteArrayOutputStream output =
                new ByteArrayOutputStream();

        bitmap.compress(
                Bitmap.CompressFormat.JPEG,
                75,
                output
        );

        bitmap.recycle();

        byte[] bytes =
                output.toByteArray();

        String base64 =
                Base64.encodeToString(
                        bytes,
                        Base64.NO_WRAP
                );

        return "data:image/jpeg;base64,"
                + base64;
    }

    // ==============================================
    // JSON ESCAPE
    // ==============================================

    private String escapeJson(
            String text
    ) {

        if (text == null) {
            return "";
        }

        return text
                .replace(
                        "\\",
                        "\\\\"
                )
                .replace(
                        "\"",
                        "\\\""
                )
                .replace(
                        "\n",
                        "\\n"
                )
                .replace(
                        "\r",
                        "\\r"
                )
                .replace(
                        "\t",
                        "\\t"
                );
    }

    // ==============================================
    // READ SERVER RESPONSE
    // ==============================================

    private String readStream(
            InputStream inputStream
    ) throws Exception {

        if (inputStream == null) {
            return "";
        }

        ByteArrayOutputStream output =
                new ByteArrayOutputStream();

        byte[] buffer =
                new byte[4096];

        int length;

        while (
                (length =
                        inputStream.read(buffer))
                        != -1
        ) {

            output.write(
                    buffer,
                    0,
                    length
            );
        }

        inputStream.close();

        return output.toString(
                StandardCharsets.UTF_8.name()
        );
    }

    // ==============================================
    // EXTRACT JSON VALUE
    // ==============================================

    private String extractJsonValue(
            String json,
            String key
    ) {

        if (json == null
                || json.isEmpty()) {

            return "";
        }

        String search =
                "\"" + key + "\"";

        int keyIndex =
                json.indexOf(search);

        if (keyIndex == -1) {
            return "";
        }

        int colon =
                json.indexOf(
                        ":",
                        keyIndex
                );

        if (colon == -1) {
            return "";
        }

        int firstQuote =
                json.indexOf(
                        "\"",
                        colon + 1
                );

        if (firstQuote == -1) {
            return "";
        }

        StringBuilder value =
                new StringBuilder();

        boolean escaped = false;

        for (
                int i = firstQuote + 1;
                i < json.length();
                i++
        ) {

            char c = json.charAt(i);

            if (escaped) {

                switch (c) {

                    case 'n':
                        value.append('\n');
                        break;

                    case 'r':
                        value.append('\r');
                        break;

                    case 't':
                        value.append('\t');
                        break;

                    case '"':
                        value.append('"');
                        break;

                    case '\\':
                        value.append('\\');
                        break;

                    default:
                        value.append(c);
                        break;
                }

                escaped = false;

            } else if (c == '\\') {

                escaped = true;

            } else if (c == '"') {

                break;

            } else {

                value.append(c);
            }
        }

        return value.toString();
    }

    // ==============================================
    // OPEN PHOTO PICKER
    // ==============================================

    private void openPhotoPicker() {

        Intent intent =
                new Intent(
                        Intent.ACTION_OPEN_DOCUMENT
                );

        intent.addCategory(
                Intent.CATEGORY_OPENABLE
        );

        intent.setType("image/*");

        startActivityForResult(
                intent,
                PICK_IMAGE
        );
    }

    // ==============================================
    // PHOTO RESULT
    // ==============================================

    @Override
    protected void onActivityResult(
            int requestCode,
            int resultCode,
            Intent data
    ) {

        super.onActivityResult(
                requestCode,
                resultCode,
                data
        );

        if (requestCode == PICK_IMAGE
                && resultCode == RESULT_OK
                && data != null) {

            Uri imageUri =
                    data.getData();

            if (imageUri != null) {

                selectedImageUri =
                        imageUri;

                questionImage.setImageURI(
                        imageUri
                );

                questionImage.setVisibility(
                        ImageView.VISIBLE
                );

                Toast.makeText(
                        this,
                        "Question photo selected ✅",
                        Toast.LENGTH_SHORT
                ).show();
            }
        }
    }
                }
