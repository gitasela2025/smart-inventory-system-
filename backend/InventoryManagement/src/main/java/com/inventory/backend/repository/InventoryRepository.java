package com.inventory.backend.repository;

import com.inventory.backend.model.Inventory;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface InventoryRepository extends JpaRepository<Inventory, Integer> {
    Inventory findByProductId(Integer productId);

    @Query("SELECT i FROM Inventory i")
    List<Inventory> findAllWithProductDetails();
}