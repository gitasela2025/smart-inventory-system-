package com.inventory.backend;

import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

public class PasswordGenerator {
    public static void main(String[] args) {
        BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();

        String password = "admin123";
        String hash = encoder.encode(password);

        System.out.println("Password: " + password);
        System.out.println("Hash: " + hash);
        System.out.println();
        System.out.println("Copy this SQL and run in MySQL Workbench:");
        System.out.println("UPDATE users SET password = '" + hash + "' WHERE username = 'admin';");

        // Verify the hash works
        boolean matches = encoder.matches(password, hash);
        System.out.println("Verification: " + (matches ? "✅ HASH IS VALID" : "❌ HASH IS INVALID"));
    }
}