package com.inventory.backend;

import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

public class BCryptGenerator {
    public static void main(String[] args) {
        BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();

        String adminHash = encoder.encode("admin123");
        String staffHash = encoder.encode("staff123");

        System.out.println("UPDATE users SET password = '" + adminHash + "' WHERE username = 'admin';");
        System.out.println("UPDATE users SET password = '" + staffHash + "' WHERE username = 'staff1';");
    }
}