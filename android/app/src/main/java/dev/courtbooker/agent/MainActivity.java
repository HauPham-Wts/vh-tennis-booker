package dev.courtbooker.agent;

import android.app.Activity;
import android.os.Bundle;

/**
 * Opened once after install: a package that was never started is "stopped", and Android does
 * not bind its accessibility service. It has nothing to show, so it closes at once.
 */
public class MainActivity extends Activity {
    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        finish();
    }
}
