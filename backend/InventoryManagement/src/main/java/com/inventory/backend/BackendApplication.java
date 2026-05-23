package com.inventory.backend;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class BackendApplication {
	public static void main(String[] args) {
		SpringApplication.run(BackendApplication.class, args);
		System.out.println("=========================================");
		System.out.println("Smart Inventory System Backend Started!");
		System.out.println("JWT Authentication is Ready!");
		System.out.println("=========================================");
	}
}