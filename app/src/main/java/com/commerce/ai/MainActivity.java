package com.commerce.ai;

import android.app.Activity;
import android.os.Bundle;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.net.Uri;
import android.provider.Settings;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {

    private static final int PICK_IMAGE = 100;

    private ImageView questionImage;
    private EditText questionInput;
    private TextView result;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        LinearLayout mainLayout = new LinearLayout(this);
        mainLayout.setOrientation(LinearLayout.VERTICAL);
        mainLayout.setPadding(30, 35, 30, 30);
        mainLayout.setBackgroundColor(Color.WHITE);

        TextView title = new TextView(this);
        title.setText("Commerce AI");
        title.setTextSize(30);
        title.setTypeface(null, Typeface.BOLD);
        title.setTextColor(Color.BLACK);
        title.setGravity(Gravity.CENTER);

        mainLayout.addView(title,
                new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT
                ));

        TextView subtitle = new TextView(this);
        subtitle.setText("Accountancy & Economics Solver");
        subtitle.setTextSize(16);
        subtitle.setTextColor(Color.DKGRAY);
        subtitle.setGravity(Gravity.CENTER);
        subtitle.setPadding(0, 8, 0, 25);

        mainLayout.addView(subtitle);

        Button photoButton = new Button(this);
        photoButton.setText("📷  Upload Question Photo");
        photoButton.setTextSize(16);

        mainLayout.addView(photoButton,
                new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT
                ));

        questionImage = new ImageView(this);
        questionImage.setVisibility(ImageView.GONE);
        questionImage.setAdjustViewBounds(true);
        questionImage.setPadding(10, 15, 10, 15);

        mainLayout.addView(questionImage,
                new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        500
                ));

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

        mainLayout.addView(questionInput, inputParams);

        Button solveButton = new Button(this);
        solveButton.setText("✨  Solve Question");
        solveButton.setTextSize(17);

        mainLayout.addView(solveButton,
                new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT
                ));

        result = new TextView(this);
        result.setText(
                "Your complete step-by-step solution will appear here."
        );
        result.setTextSize(16);
        result.setTextColor(Color.DKGRAY);
        result.setPadding(10, 30, 10, 10);

        mainLayout.addView(result);

        setContentView(mainLayout);

        photoButton.setOnClickListener(view -> openPhotoPicker());

        solveButton.setOnClickListener(view -> {

            String question =
                    questionInput.getText().toString().trim();

            if (question.isEmpty()
                    && questionImage.getVisibility() == ImageView.GONE) {

                Toast.makeText(
                        MainActivity.this,
                        "Photo upload karo ya question type karo.",
                        Toast.LENGTH_SHORT
                ).show();

                return;
            }

            result.setText(
                    "Question received!\n\n" +
                    "AI solving system next step mein connect hoga.\n\n" +
                    "Abhi photo upload aur question input working hai."
            );
        });
    }

    private void openPhotoPicker() {

        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);

        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("image/*");

        startActivityForResult(intent, PICK_IMAGE);
    }

    @Override
    protected void onActivityResult(
            int requestCode,
            int resultCode,
            Intent data) {

        super.onActivityResult(
                requestCode,
                resultCode,
                data
        );

        if (requestCode == PICK_IMAGE
                && resultCode == RESULT_OK
                && data != null) {

            Uri imageUri = data.getData();

            if (imageUri != null) {

                questionImage.setImageURI(imageUri);
                questionImage.setVisibility(ImageView.VISIBLE);

                Toast.makeText(
                        this,
                        "Question photo selected ✅",
                        Toast.LENGTH_SHORT
                ).show();
            }
        }
    }
}
