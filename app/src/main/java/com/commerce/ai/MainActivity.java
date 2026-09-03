<?xml version="1.0" encoding="utf-8"?>

<LinearLayout
    xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:padding="20dp">

    <TextView
        android:id="@+id/titleText"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="Commerce AI"
        android:textSize="28sp"
        android:textStyle="bold"
        android:gravity="center"/>

    <TextView
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="Accountancy &amp; Economics Solver"
        android:textSize="16sp"
        android:gravity="center"
        android:layout_marginBottom="20dp"/>

    <Button
        android:id="@+id/uploadButton"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="📷 UPLOAD QUESTION PHOTO"/>

    <EditText
        android:id="@+id/questionInput"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:hint="Or type your question here..."
        android:gravity="top"
        android:minHeight="100dp"
        android:padding="12dp"
        android:layout_marginTop="12dp"/>

    <Button
        android:id="@+id/solveButton"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="✨ SOLVE QUESTION"
        android:layout_marginTop="12dp"/>

    <!-- DETAILED ANSWER SCROLL AREA -->
    <ScrollView
        android:id="@+id/resultScroll"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1"
        android:layout_marginTop="15dp"
        android:fillViewport="true">

        <TextView
            android:id="@+id/resultText"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:text="Solution will appear here..."
            android:textSize="16sp"
            android:lineSpacingExtra="5dp"
            android:padding="14dp"
            android:textIsSelectable="true"/>

    </ScrollView>

</LinearLayout>
