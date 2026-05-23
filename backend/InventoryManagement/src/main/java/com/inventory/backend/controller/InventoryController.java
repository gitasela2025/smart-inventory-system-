package com.inventory.backend.controller;

import com.inventory.backend.model.Inventory;
import com.inventory.backend.model.Product;
import com.inventory.backend.repository.InventoryRepository;
import com.inventory.backend.repository.ProductRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/inventory")
@CrossOrigin(origins = "http://localhost:3000")
public class InventoryController {

    @Autowired
    private InventoryRepository inventoryRepository;

    @Autowired
    private ProductRepository productRepository;

    @GetMapping
    public List<Map<String, Object>> getAllInventory() {
        List<Inventory> inventoryList = inventoryRepository.findAll();
        List<Map<String, Object>> result = new ArrayList<>();

        for (Inventory inv : inventoryList) {
            Map<String, Object> item = new HashMap<>();
            item.put("id", inv.getId());
            item.put("product_id", inv.getProductId());
            item.put("quantity", inv.getQuantity());
            item.put("reorder_level", inv.getReorderLevel());
            item.put("reorder_quantity", inv.getReorderQuantity());

            // Get product details
            Product product = productRepository.findById(inv.getProductId()).orElse(null);
            if (product != null) {
                item.put("product_name", product.getName());
                item.put("category", product.getCategory());
                item.put("unit_price", product.getUnitPrice());
            } else {
                item.put("product_name", "Unknown");
                item.put("category", "Unknown");
                item.put("unit_price", 0);
            }

            result.add(item);
        }
        return result;
    }

    @PutMapping("/{productId}")
    public Map<String, Object> updateStock(@PathVariable Integer productId, @RequestBody Map<String, Integer> request) {
        Integer quantity = request.get("quantity");
        Inventory inventory = inventoryRepository.findByProductId(productId);

        Map<String, Object> response = new HashMap<>();

        if (inventory != null) {
            inventory.setQuantity(quantity);
            inventoryRepository.save(inventory);
            response.put("success", true);
            response.put("message", "Stock updated successfully");
        } else {
            response.put("success", false);
            response.put("message", "Inventory not found");
        }
        return response;
    }
}