package com.commerce.ai;

import android.app.Activity;
import android.os.Bundle;
import android.graphics.Color;
import android.graphics.Typeface;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;

public class MainActivity extends Activity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        LinearLayout mainLayout = new LinearLayout(this);
        mainLayout.setOrientation(LinearLayout.VERTICAL);
        mainLayout.setPadding(30, 40, 30, 30);
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
        subtitle.setGravity(Gravity.CENTER);
        subtitle.setPadding(0, 10, 0, 35);

        mainLayout.addView(subtitle);

        Button photoButton = new Button(this);
        photoButton.setText("📷  Upload Question Photo");

        mainLayout.addView(photoButton,
                new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT
                ));

        EditText questionInput = new EditText(this);
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

        inputParams.setMargins(0, 25, 0, 20);

        mainLayout.addView(questionInput, inputParams);

        Button solveButton = new Button(this);
        solveButton.setText("✨  Solve Question");
        solveButton.setTextSize(17);

        mainLayout.addView(solveButton,
                new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT
                ));

        TextView result = new TextView(this);
        result.setText(
                "Your complete step-by-step solution will appear here."
        );
        result.setTextSize(16);
        result.setTextColor(Color.DKGRAY);
        result.setPadding(10, 35, 10, 10);

        mainLayout.addView(result);

        setContentView(mainLayout);
    }
}
